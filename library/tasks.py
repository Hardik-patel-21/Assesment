from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Loan, Backlink
import gzip
import json
from pathlib import Path

import logging

logger = logging.getLogger(__name__)


@shared_task
def send_loan_notification(loan_id):
    try:
        loan = Loan.objects.select_related(
            'member__user',
            'book'
        ).get(id=loan_id)

        member_email = loan.member.user.email

        if not member_email:
            logger.warning(
                f"No email found for loan {loan_id}"
            )
            return

        book_title = loan.book.title

        send_mail(
            subject='Book Loaned Successfully',
            message=(
                f'Hello {loan.member.user.username},\n\n'
                f'You have successfully loaned "{book_title}".\n'
                f'Please return it by the due date.'
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[member_email],
            fail_silently=False
        )

        logger.info(
            f"Loan notification sent to {member_email} for loan {loan_id}"
        )

    except Loan.DoesNotExist:
        logger.error(
            f"Loan {loan_id} does not exist."
        )

    except Exception as e:
        logger.exception(
            f"Error sending loan notification for loan {loan_id}: {e}"
        )


@shared_task
def check_overdue_loans():
    try:
        overdue_loans = Loan.objects.select_related(
            'member__user',
            'book'
        ).filter(
            is_returned=False,
            due_date__lt=timezone.now().date()
        )

        logger.info(
            f"Found {overdue_loans.count()} overdue loans"
        )

        for loan in overdue_loans:

            try:
                member_email = loan.member.user.email

                if not member_email:
                    logger.warning(
                        f"No email for overdue loan {loan.id}"
                    )
                    continue

                send_mail(
                    subject='Overdue Book Reminder',
                    message=(
                        f'Hello {loan.member.user.username},\n\n'
                        f'Book "{loan.book.title}" is overdue.\n'
                        f'Please return it as soon as possible.'
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[member_email],
                    fail_silently=False
                )

                logger.info(
                    f"Overdue reminder sent for loan {loan.id}"
                )

            except Exception as e:
                logger.exception(
                    f"Failed processing overdue loan {loan.id}: {e}"
                )

    except Exception as e:
        logger.exception(
            f"check_overdue_loans failed: {e}"
        )

@shared_task
def build_backlink_graph():

    wat_file = (
        Path(settings.BASE_DIR)
        / "data"
        / "sample.wat.gz"
    )

    if not wat_file.exists():
        logger.error(
            f"WAT file not found: {wat_file}"
        )
        return

    created_count = 0

    try:

        with gzip.open(
            wat_file,
            "rt",
            encoding="utf-8",
            errors="ignore"
        ) as f:

            for line in f:

                line = line.strip()

                if not line.startswith("{"):
                    continue

                try:
                    record = json.loads(line)

                except Exception:
                    continue

                envelope = record.get(
                    "Envelope",
                    {}
                )

                warc = envelope.get(
                    "WARC-Header-Metadata",
                    {}
                )

                payload = envelope.get(
                    "Payload-Metadata",
                    {}
                )

                response_meta = payload.get(
                    "HTTP-Response-Metadata",
                    {}
                )

                html_meta = response_meta.get(
                    "HTML-Metadata",
                    {}
                )

                source_url = warc.get(
                    "WARC-Target-URI"
                )

                links = html_meta.get(
                    "Links",
                    []
                )

                if not source_url:
                    continue

                for link in links:

                    target_url = link.get(
                        "url"
                    )

                    anchor_text = (
                        link.get("text")
                        or ""
                    )

                    if not target_url:
                        continue

                    _, created = Backlink.objects.get_or_create(
                        source_url=source_url,
                        target_url=target_url,
                        defaults={
                            "anchor_text": anchor_text
                        }
                    )

                    if created:
                        created_count += 1

        logger.info(
            f"Backlinks created: {created_count}"
        )

    except Exception as e:

        logger.exception(
            f"Backlink parsing failed: {e}"
        )