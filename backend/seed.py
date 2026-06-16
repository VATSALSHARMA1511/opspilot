import random
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

random.seed(42)

from faker import Faker
from datetime import datetime, timezone, timedelta

from app.db.session import SessionLocal
from app.models.user import User
from app.models.ticket import Ticket, TicketComment
from app.models.enums import UserRole, TicketStatus, TicketPriority
from app.core.security import hash_password

fake = Faker()
fake.seed_instance(42)

# ---------------------------------------------------------------------------
# Realistic IT ticket data
# ---------------------------------------------------------------------------
IT_TITLES = [
    "Laptop not connecting to VPN",
    "Outlook not syncing emails",
    "Need access to SharePoint",
    "Printer offline on 3rd floor",
    "Excel crashing on startup",
    "Cannot login to SAP",
    "Monitor not detected after docking",
    "Slow internet on 4th floor",
    "Teams calls dropping every few minutes",
    "Password reset not working",
    "OneDrive not syncing files",
    "Blue screen of death on Dell laptop",
    "Need software installed — Adobe Acrobat",
    "USB ports not working on workstation",
    "Cannot access shared network drive",
    "Zoom audio not working in meeting room",
    "New employee laptop setup required",
    "Email account locked after failed logins",
    "Scanner not showing up on network",
    "VPN slow during peak hours",
    "Cannot print from MacBook",
    "Need access to HR portal",
    "Antivirus flagging legitimate software",
    "Keyboard and mouse not pairing via Bluetooth",
    "Two-factor authentication not working",
    "Screen flickering on laptop display",
    "Need to recover deleted files from shared drive",
    "Office 365 license expired for user",
    "Webcam not detected in Teams",
    "Cannot open PDF attachments in Outlook",
    "System running very slow after Windows update",
    "Need VPN account created for new joiner",
    "Projector not connecting in conference room B",
    "Cannot access company intranet from home",
    "Mobile device not syncing with Exchange",
]

IT_DESCRIPTIONS = [
    "The issue started this morning after a system restart. Tried basic troubleshooting steps with no success.",
    "This has been happening intermittently for the past week. It affects my daily work significantly.",
    "Urgent — needed for client presentation tomorrow. Please prioritize.",
    "Multiple users on the same floor are reporting the same issue.",
    "This worked fine until the last IT update was pushed.",
    "I followed the standard troubleshooting guide but the problem persists.",
    "The error message shown is: connection timed out / access denied / device not found.",
    "This is blocking me from completing my month-end reports.",
    "I have already restarted the machine twice. No change.",
    "The issue is reproducible every time I try.",
]

RESOLUTION_NOTES = [
    "Resolved by updating network adapter drivers and flushing DNS cache.",
    "Issue fixed after re-configuring Outlook profile and clearing cached credentials.",
    "Access provisioned via Active Directory group policy. User confirmed working.",
    "Printer driver reinstalled and port settings corrected. Tested successfully.",
    "Root cause was a corrupted Office installation. Repaired via Control Panel.",
    "SAP credentials reset and role reassigned by basis team.",
    "Display driver updated to latest version. Monitor detected after reboot.",
    "ISP-side congestion confirmed and escalated to network team. Resolved after ISP fix.",
    "Teams client reinstalled. Issue was caused by outdated cache files.",
    "Password reset completed via AD. Enforced password change on next login.",
]

DEPARTMENTS = ["IT", "HR", "Finance"]
ALL_STATUSES = list(TicketStatus)
ALL_PRIORITIES = list(TicketPriority)


def run_seed():
    db = SessionLocal()
    try:
        # -----------------------------------------------------------------------
        # Check idempotency
        # -----------------------------------------------------------------------
        existing_users = db.query(User).count()
        if existing_users >= 10:
            print(f"Seed data already exists ({existing_users} users found). Skipping.")
            return

        # -----------------------------------------------------------------------
        # Create users
        # -----------------------------------------------------------------------
        users_created = 0
        created_users = []

        user_specs = (
            [(UserRole.ADMIN, "IT"), (UserRole.ADMIN, "HR")] +
            [(UserRole.AGENT, random.choice(DEPARTMENTS)) for _ in range(5)] +
            [(UserRole.VIEWER, random.choice(DEPARTMENTS)) for _ in range(3)]
        )

        for role, dept in user_specs:
            first = fake.first_name()
            last = fake.last_name()
            email = f"{first.lower()}.{last.lower()}.{random.randint(10,99)}@opspilot.internal"
            user = User(
                email=email,
                hashed_password=hash_password("password123"),
                full_name=f"{first} {last}",
                role=role,
                department=dept,
                is_active=True,
            )
            db.add(user)
            created_users.append(user)
            users_created += 1

        db.flush()

        agents_and_admins = [u for u in created_users if u.role in (UserRole.AGENT, UserRole.ADMIN)]
        all_users = created_users

        # -----------------------------------------------------------------------
        # Create tickets
        # -----------------------------------------------------------------------
        tickets_created = 0
        created_tickets = []

        # Distribute 200 tickets across statuses evenly-ish
        status_pool = (ALL_STATUSES * 40)[:200]
        random.shuffle(status_pool)

        priority_pool = (ALL_PRIORITIES * 50)[:200]
        random.shuffle(priority_pool)

        for i in range(200):
            status = status_pool[i]
            priority = priority_pool[i]
            creator = random.choice(all_users)
            assignee = random.choice(agents_and_admins) if status != TicketStatus.OPEN else None

            is_resolved = status in (TicketStatus.RESOLVED, TicketStatus.CLOSED)
            created_days_ago = random.randint(1, 90)
            created_at = datetime.now(timezone.utc) - timedelta(days=created_days_ago)
            resolved_at = created_at + timedelta(hours=random.randint(2, 72)) if is_resolved else None

            ticket = Ticket(
                title=random.choice(IT_TITLES),
                description=random.choice(IT_DESCRIPTIONS),
                status=status,
                priority=priority,
                category=random.choice(["Hardware", "Software", "Network", "Access", "Email", "Other"]),
                created_by_id=creator.id,
                assigned_to_id=assignee.id if assignee else None,
                resolution_notes=random.choice(RESOLUTION_NOTES) if is_resolved else None,
                created_at=created_at,
                updated_at=created_at,
                resolved_at=resolved_at,
            )
            db.add(ticket)
            created_tickets.append(ticket)
            tickets_created += 1

        db.flush()

        # -----------------------------------------------------------------------
        # Create comments
        # -----------------------------------------------------------------------
        comments_created = 0

        for i in range(400):
            ticket = random.choice(created_tickets)
            author = random.choice(all_users)
            is_internal = random.random() < 0.3  # 30% internal

            # viewers can't write internal comments
            if author.role == UserRole.VIEWER:
                is_internal = False

            comment = TicketComment(
                ticket_id=ticket.id,
                author_id=author.id,
                body=fake.paragraph(nb_sentences=random.randint(1, 3)),
                is_internal=is_internal,
                created_at=ticket.created_at + timedelta(hours=random.randint(1, 48)),
            )
            db.add(comment)
            comments_created += 1

        db.commit()

        # -----------------------------------------------------------------------
        # Summary
        # -----------------------------------------------------------------------
        print("\n✅ Seed complete!")
        print(f"   Users created    : {users_created}")
        print(f"     Admins         : {sum(1 for u in created_users if u.role == UserRole.ADMIN)}")
        print(f"     Agents         : {sum(1 for u in created_users if u.role == UserRole.AGENT)}")
        print(f"     Viewers        : {sum(1 for u in created_users if u.role == UserRole.VIEWER)}")
        print(f"   Tickets created  : {tickets_created}")
        for s in ALL_STATUSES:
            count = sum(1 for t in created_tickets if t.status == s)
            print(f"     {s.value:<12}: {count}")
        print(f"   Comments created : {comments_created}")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
