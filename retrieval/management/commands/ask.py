from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from machines.models import Machine
from retrieval.llm import LLMUnavailable
from retrieval.services import answer_question

User = get_user_model()


class Command(BaseCommand):
    help = 'Ask a question from the terminal, e.g. manage.py ask 1 "How often is the gasket replaced?"'

    def add_arguments(self, parser):
        parser.add_argument("machine_id", type=int)
        parser.add_argument("question")
        parser.add_argument("--user", default="engineer_demo")

    def handle(self, *args, **options):
        try:
            machine = Machine.objects.get(pk=options["machine_id"])
            user = User.objects.get(username=options["user"])
        except (Machine.DoesNotExist, User.DoesNotExist) as error:
            raise CommandError(str(error))

        try:
            question = answer_question(user, machine, options["question"])
        except LLMUnavailable as error:
            raise CommandError(f"The AI service is not available: {error}")

        self.stdout.write(f"\nMachine  : {machine}")
        self.stdout.write(f"Answered : {question.answered}")
        self.stdout.write(f"Answer   : {question.answer}\n")

        for source in question.sources.all():
            self.stdout.write(
                f"  [{source.passage_number}] {source.manual_name}, "
                f"revision {source.revision}, page {source.page_number} "
                f"(score {source.score})"
            )
            self.stdout.write(f"      {source.text[:160]}...")
