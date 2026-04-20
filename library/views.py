from datetime import timedelta
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from .models import Author, Book, Member, Loan, Backlink
from .serializers import AuthorSerializer, BookSerializer, MemberSerializer, LoanSerializer, BacklinkSerializer
from .tasks import send_loan_notification


class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer


class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.select_related('author').all()
    serializer_class = BookSerializer

    @action(detail=True, methods=['post'])
    def loan(self, request, pk=None):
        member_id = request.data.get('member_id')
        if not member_id:
            return Response(
                {'error': 'member_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return Response(
                {'error': 'Member does not exist.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            book = Book.objects.select_for_update().select_related('author').get(pk=pk)

            if book.available_copies < 1:
                return Response(
                    {'error': 'No available copies.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            loan = Loan.objects.create(book=book, member=member)
            book.available_copies -= 1
            book.save(update_fields=['available_copies'])

        send_loan_notification.delay(loan.id)

        return Response(
            {'status': 'Book loaned successfully.'},
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        member_id = request.data.get('member_id')
        if not member_id:
            return Response(
                {'error': 'member_id is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            book = Book.objects.select_for_update().get(pk=pk)

            try:
                loan = Loan.objects.select_for_update().get(
                    book=book,
                    member__id=member_id,
                    is_returned=False
                )
            except Loan.DoesNotExist:
                return Response(
                    {'error': 'Active loan does not exist.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            loan.is_returned = True
            loan.return_date = timezone.now().date()
            loan.save(update_fields=['is_returned', 'return_date'])

            book.available_copies += 1
            book.save(update_fields=['available_copies'])

        return Response(
            {'status': 'Book returned successfully.'},
            status=status.HTTP_200_OK
        )


class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer

    @action(detail=False, methods=['get'], url_path='top-active')
    def top_active(self, request):

        members = Member.objects.annotate(
            active_loans=Count(
                'loans',
                filter=Q(loans__is_returned=False)
            )
        ).order_by(
            '-active_loans',
            'id'
        )[:5]

        data = [
            {
                'id': member.id,
                'username': member.user.username,
                'active_loans': member.active_loans
            }
            for member in members
        ]

        return Response(data)


class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.select_related('book', 'member', 'member__user', 'book__author').all()
    serializer_class = LoanSerializer

    @action(detail=True, methods=['post'])
    def extend_due_date(self, request, pk=None):

        loan = self.get_object()

        additional_days = request.data.get('additional_days')

        try:
            additional_days = int(additional_days)
        except (TypeError, ValueError):
            raise ValidationError(
                "additional_days must be a positive integer."
            )

        if additional_days <= 0:
            raise ValidationError(
                "additional_days must be a positive integer."
            )

        if loan.due_date < timezone.now().date():
            raise ValidationError(
                "Loan is already overdue."
            )

        loan.due_date += timedelta(days=additional_days)

        loan.save(
            update_fields=['due_date']
        )

        return Response(
            {
                "id": loan.id,
                "status": "Due date extended",
                "new_due_date": loan.due_date,
                "additional_days": additional_days
            },
            status=status.HTTP_200_OK
        )

class BacklinkViewSet(
    viewsets.ReadOnlyModelViewSet
):
    queryset = Backlink.objects.all().order_by("id")
    serializer_class = BacklinkSerializer