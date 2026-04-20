from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from library.models import Author, Book, Member, Loan
from django.utils import timezone
from datetime import timedelta

# Create your tests here.
class LoanExtendDueDateTest(TestCase):

    def setUp(self):

        self.client = APIClient()

        self.user = User.objects.create_user(
            username="john",
            password="test123"
        )

        self.member = Member.objects.create(
            user=self.user
        )

        self.author = Author.objects.create(
            first_name="George",
            last_name="Orwell"
        )

        self.book = Book.objects.create(
            title="1984",
            author=self.author,
            isbn="1234567890123",
            genre="fiction",
            available_copies=2
        )

        self.loan = Loan.objects.create(
            book=self.book,
            member=self.member,
            due_date=timezone.now().date() + timedelta(days=5),
            is_returned=False
        )

    def test_extend_due_date_success(self):

        url = f"/api/loans/{self.loan.id}/extend_due_date/"

        response = self.client.post(
            url,
            {"additional_days": 7},
            format="json"
        )

        self.assertEqual(
            response.status_code,
            200
        )

        self.loan.refresh_from_db()

        self.assertEqual(
            self.loan.due_date,
            timezone.now().date() + timedelta(days=12)
        )