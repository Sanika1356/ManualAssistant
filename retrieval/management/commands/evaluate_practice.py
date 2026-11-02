"""
Runs a list of practice questions and suggests a value for RAG_MIN_SCORE.

    python manage.py evaluate_practice
    python manage.py evaluate_practice --with-llm

Each question in the JSON file looks like this:
    {"machine": "Kitchen A", "question": "...",
     "expect": "answerable" | "other_machine" | "unsupported",
     "keyword": "text the correct passage or answer must contain"}
"""
import json

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from machines.models import Machine
from retrieval import services, vectorstore
from retrieval.llm import LLMUnavailable
from retrieval.models import Question

User = get_user_model()


def suggest_threshold(answerable_scores, refused_scores):
    """
    Pick a threshold that separates the two groups of scores.
    Returns (threshold, clean_gap).
    """
    lowest_answerable = min(answerable_scores)
    highest_refused = max(refused_scores)

    # Best case: every answerable question scores above every refused one.
    if lowest_answerable > highest_refused:
        return round((lowest_answerable + highest_refused) / 2, 3), True

    # Otherwise pick the value that gets the most questions right.
    all_scores = answerable_scores + refused_scores
    best_value, best_correct = all_scores[0], -1
    for value in sorted(set(all_scores)):
        correct = sum(score >= value for score in answerable_scores)
        correct += sum(score < value for score in refused_scores)
        if correct > best_correct:
            best_value, best_correct = value, correct
    return round(best_value, 3), False


class Command(BaseCommand):
    help = "Run the practice questions and suggest a RAG_MIN_SCORE."

    def add_arguments(self, parser):
        parser.add_argument("--file", default="rehearsal/practice_questions.json")
        parser.add_argument("--with-llm", action="store_true",
                            help="Also call the AI model for each question.")
        parser.add_argument("--threshold", type=float, default=None,
                            help="Try a specific threshold instead of the one in settings.")

    def handle(self, *args, **options):
        try:
            with open(options["file"], encoding="utf-8") as file:
                questions = json.load(file)
        except (OSError, ValueError) as error:
            raise CommandError(f"Could not read {options['file']}: {error}")

        threshold = options["threshold"]
        if threshold is None:
            threshold = float(settings.RAG_MIN_SCORE)

        answerable_scores, refused_scores = [], []
        wrong_count = 0

        # With --with-llm the questions go through the full pipeline, which
        # saves them. A temporary user is used so they can be cleaned up after.
        runner = None
        if options["with_llm"]:
            runner, _ = User.objects.get_or_create(username="practice_runner")

        self.stdout.write(f"Threshold in use: {threshold}\n")
        self.stdout.write(f"{'expected':<15}{'score':>6}  {'result':<7} question")

        for item in questions:
            machine = Machine.objects.filter(name__icontains=item["machine"]).first()
            if machine is None:
                raise CommandError(f"No machine found matching {item['machine']!r}")

            expected = item["expect"]
            keyword = (item.get("keyword") or "").lower()

            hits = vectorstore.search(machine.id, item["question"], k=settings.RAG_TOP_K)
            best_score = hits[0].score if hits else 0.0
            if expected == "answerable":
                answerable_scores.append(best_score)
            else:
                refused_scores.append(best_score)

            if options["with_llm"]:
                try:
                    saved = services.answer_question(runner, machine, item["question"])
                except LLMUnavailable as error:
                    raise CommandError(f"The AI service is not available: {error}")
                answered = saved.answered
                has_keyword = keyword in saved.answer.lower()
            else:
                answered = best_score >= threshold
                top_text = " ".join(hit.text for hit in hits[:2]).lower()
                has_keyword = keyword in top_text

            if expected == "answerable":
                correct = answered and has_keyword
            else:
                correct = not answered

            if not correct:
                wrong_count += 1

            style = self.style.SUCCESS if correct else self.style.ERROR
            self.stdout.write(style(
                f"{expected:<15}{best_score:>6.3f}  "
                f"{'OK' if correct else 'WRONG':<7} {item['question'][:70]}"
            ))

        if runner:
            Question.objects.filter(user=runner).delete()
            runner.delete()

        self.stdout.write("")
        if answerable_scores and refused_scores:
            suggested, clean_gap = suggest_threshold(answerable_scores, refused_scores)
            self.stdout.write(f"Lowest score of an answerable question : {min(answerable_scores):.3f}")
            self.stdout.write(f"Highest score of a refused question    : {max(refused_scores):.3f}")
            if clean_gap:
                self.stdout.write(self.style.SUCCESS(
                    f"Clean gap found. Suggested RAG_MIN_SCORE={suggested}"
                ))
            else:
                self.stdout.write(self.style.WARNING(
                    f"The scores overlap. Best result at RAG_MIN_SCORE={suggested}. "
                    "Run with --with-llm so the model's own check helps with the rest."
                ))

        self.stdout.write(f"\n{len(questions) - wrong_count} of {len(questions)} behaved correctly.")
