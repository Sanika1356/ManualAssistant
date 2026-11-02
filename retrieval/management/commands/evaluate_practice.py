"""
Runs the practice questions and reports OK or WRONG for each one.
It also suggests a value for RAG_MIN_SCORE.

    python manage.py evaluate_practice
    python manage.py evaluate_practice --with-llm
    python manage.py evaluate_practice --file rehearsal/practice_questions_real.json

Each question in the JSON file looks like this:
    {"id": 13, "machine": "HP-200", "question": "...",
     "expect_status": "answered" | "insufficient_evidence",
     "keywords": ["text that must appear"],
     "sources": [{"doc": "HP-OPS-01", "page": 2}, {"doc": "HP-MNT-01", "page": 3}],
     "note": "free text for the team"}

"machine" is matched against the machine model first (for example HP-200),
then against the machine name.
"""
import json
import re

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from machines.models import Machine
from retrieval import services, vectorstore
from retrieval.llm import LLMUnavailable
from retrieval.models import Question

User = get_user_model()

DOCUMENT_IDS = ("HP-OPS-01", "HP-MNT-01", "AC-OM-01")


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


def normalise(text):
    """Lower case and single spaces, so '110  BAR' matches '110 bar'."""
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def find_machine(label):
    machine = Machine.objects.filter(model__iexact=label).first()
    if machine is None:
        machine = Machine.objects.filter(name__icontains=label).first()
    return machine


def _id_text(item):
    """The words that can identify the document of a hit or a saved source."""
    parts = [
        getattr(item, "document_id", "") or "",
        getattr(item, "manual_name", "") or "",
    ]
    return " ".join(parts).upper()


def check_sources(expected_sources, found):
    """
    found is a list of (id_text, page) pairs.
    Returns (problems, page_only). When the document IDs are not in the data
    yet (before Person 2 adds them), only the page numbers can be checked.
    """
    page_only = not any(
        code in id_text for id_text, _page in found for code in DOCUMENT_IDS
    )
    problems = []
    for source in expected_sources:
        doc = source["doc"].upper()
        page = source["page"]
        ok = any(
            found_page == page and (page_only or doc in id_text)
            for id_text, found_page in found
        )
        if not ok:
            problems.append(f"missing {source['doc']} p{page}")
    return problems, page_only


def check_keywords(keywords, text):
    blob = normalise(text)
    return [f"missing '{word}'" for word in keywords if normalise(word) not in blob]


class Command(BaseCommand):
    help = "Run the practice questions and suggest a RAG_MIN_SCORE."

    def add_arguments(self, parser):
        parser.add_argument("--file", default="rehearsal/practice_questions_real.json")
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
        wrong = []
        page_only_used = False

        # With --with-llm the questions go through the full pipeline, which
        # saves them. A temporary user is used so they can be cleaned up after.
        runner = None
        if options["with_llm"]:
            runner, _ = User.objects.get_or_create(username="practice_runner")

        self.stdout.write(f"Threshold in use: {threshold}\n")
        self.stdout.write(f"{'#':>3} {'machine':<7} {'expected':<22}{'score':>6}  {'result':<6} question")

        for item in questions:
            machine = find_machine(item["machine"])
            if machine is None:
                raise CommandError(f"No machine found matching {item['machine']!r}")

            expected = item["expect_status"]
            keywords = item.get("keywords", [])
            expected_sources = item.get("sources", [])

            hits = vectorstore.search(machine.id, item["question"], k=settings.RAG_TOP_K)
            best_score = hits[0].score if hits else 0.0
            if expected == "answered":
                answerable_scores.append(best_score)
            else:
                refused_scores.append(best_score)

            problems = []

            if options["with_llm"]:
                try:
                    saved = services.answer_question(runner, machine, item["question"])
                except LLMUnavailable as error:
                    raise CommandError(f"The AI service is not available: {error}")
                got_status = "answered" if saved.answered else "insufficient_evidence"
                saved_sources = list(saved.sources.all())
                found = [(_id_text(s), s.page_number) for s in saved_sources]
                text = saved.answer + " " + " ".join(s.text for s in saved_sources)
            else:
                # No AI: judge only what the search would hand to the AI.
                got_status = "answered" if best_score >= threshold else "insufficient_evidence"
                used = [hit for hit in hits if hit.score >= threshold]
                found = [(_id_text(hit), hit.page) for hit in used]
                text = " ".join(hit.text for hit in used)

            if got_status != expected:
                problems.append(f"status is {got_status}, expected {expected}")

            if expected == "answered":
                problems += check_keywords(keywords, text)
                source_problems, page_only = check_sources(expected_sources, found)
                page_only_used = page_only_used or page_only
                problems += source_problems

            correct = not problems
            if not correct:
                wrong.append(item.get("id", "?"))

            style = self.style.SUCCESS if correct else self.style.ERROR
            self.stdout.write(style(
                f"{item.get('id', ''):>3} {item['machine']:<7} {expected:<22}"
                f"{best_score:>6.3f}  {'OK' if correct else 'WRONG':<6} {item['question'][:60]}"
            ))
            for problem in problems:
                self.stdout.write(style(f"      - {problem}"))

        if runner:
            Question.objects.filter(user=runner).delete()
            runner.delete()

        self.stdout.write("")
        if page_only_used:
            self.stdout.write(self.style.WARNING(
                "Note: document IDs are not in the data yet, so sources were "
                "checked by page number only."
            ))
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

        self.stdout.write(f"\n{len(questions) - len(wrong)} of {len(questions)} behaved correctly.")
        if wrong:
            self.stdout.write(f"Wrong question numbers: {', '.join(str(n) for n in wrong)}")
