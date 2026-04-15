from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Author, Book, Member, Loan
from .serializers import AuthorSerializer, BookSerializer, MemberSerializer, LoanSerializer
from rest_framework.decorators import action
from django.utils import timezone
from .tasks import send_loan_notification
from rest_framework.exceptions import ValidationError
from django.db import transaction

class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.all()
    serializer_class = AuthorSerializer

class BookViewSet(viewsets.ModelViewSet):
    queryset = Book.objects.all().select_related('author')
    serializer_class = BookSerializer

    @action(detail=True, methods=['post'])
    def loan(self, request, pk=None):
        book = self.get_object()
        if book.available_copies < 1:
            return Response({'error': 'No available copies.'}, status=status.HTTP_400_BAD_REQUEST)
        member_id = request.data.get('member_id')
        try:
            member = Member.objects.get(id=member_id)
        except Member.DoesNotExist:
            return Response({'error': 'Member does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan = Loan.objects.create(book=book, member=member)
        book.available_copies -= 1
        book.save()
        send_loan_notification.delay(loan.id)
        return Response({'status': 'Book loaned successfully.'}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def return_book(self, request, pk=None):
        book = self.get_object()
        member_id = request.data.get('member_id')
        try:
            loan = Loan.objects.get(book=book, member__id=member_id, is_returned=False)
        except Loan.DoesNotExist:
            return Response({'error': 'Active loan does not exist.'}, status=status.HTTP_400_BAD_REQUEST)
        loan.is_returned = True
        loan.return_date = timezone.now().date()
        loan.save()
        book.available_copies += 1
        book.save()
        return Response({'status': 'Book returned successfully.'}, status=status.HTTP_200_OK)
    #changes
        with transaction.atomic():
            loan=self.get_object()
            if loan.is_returned:
                raise ValidationError("The book has already been returned.")
            loan.is_returned=True
            loan.save()
            return Response({"status":"Book returned successfully"})


class MemberViewSet(viewsets.ModelViewSet):
    queryset = Member.objects.all()
    serializer_class = MemberSerializer
    @action(detail=True, methods=['get'])
    def top_active_members(self,request):
        members=Member.objects.annotate(
            active_loans=Count('loan', filter=Loan.objects.filter(is_returned=False))
        ).order_by('-active_loans')[:5]

        data=[{'id':member.id, 'username': member.username, 'active_loans':member.active_loans} for member in members]
        return Response(data)

class LoanViewSet(viewsets.ModelViewSet):
    queryset = Loan.objects.all().select_related('book','member')
    serializer_class = LoanSerializer
    @action(detail=True, methods=['post'])
    def extend_due_date(self,request, pk=None):
        loan=self.get_object()
        additional_days=request.data.get('additional_days',0)
        if loan.due_date<timezone.now().date():
            raise ValidationError("Loan is already overdue.")
        if additional_days<=0:
            raise ValidationError("Additional days must be a positive integer.")
        loan.due_date+=timedelta(days=additional_days)
        loan.save()

        return Response({
            'status':'Due date extended',
            'new_due_date':loan.due_date
        },status=status.HTTP_200_OK)