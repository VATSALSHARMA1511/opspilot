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
from app.models.department import Department
from app.models.enums import UserRole, TicketStatus, TicketPriority, ManagerAction
from app.core.security import hash_password

fake = Faker()
fake.seed_instance(42)

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
    "Blue screen of death on Dell laptop",
    "USB ports not working on workstation",
    "Cannot access shared network drive",
    "Zoom audio not working in meeting room",
    "New employee laptop setup required",
    "Scanner not showing up on network",
    "Screen flickering on laptop display",
    "Need to recover deleted files",
    "Webcam not detected in Teams",
    "Cannot open PDF attachments in Outlook",
]

HR_TITLES = [
    "Leave balance incorrect in portal",
    "Payslip not generated for last month",
    "Need experience letter",
    "Onboarding documents missing",
    "Medical reimbursement claim pending",
    "Need to update emergency contact",
    "Training certification not updated",
    "Attendance marked wrong for last week",
]

ACCOUNTS_TITLES = [
    "Invoice not processed",
    "Vendor payment overdue",
    "Expense report not reimbursed",
    "GST filing query",
    "Budget approval pending",
    "PO not raised for approved project",
    "TDS certificate not issued",
]

SECURITY_TITLES = [
    "Suspicious login attempt on account",
    "Need access card for new employee",
    "CCTV not working on floor 2",
    "Data breach concern in shared folder",
    "VPN credentials compromised",
    "Need to revoke access for ex-employee",
]

DESCRIPTIONS = [
    "The issue started this morning after a system restart. Tried basic troubleshooting with no success.",
    "This has been happening intermittently for the past week and affects daily work significantly.",
    "Urgent — needed for client deliverable tomorrow. Please prioritize.",
    "Multiple users on the same floor are reporting the same issue.",
    "This worked fine until the last update was pushed.",
    "I followed the standard process but the problem persists.",
    "This is blocking me from completing my month-end reports.",
    "I have already restarted the machine twice with no change.",
    "The issue is reproducible every time I try.",
    "Please look into this at the earliest convenience.",
]

RESOLUTION_NOTES = [
    "Resolved by updating drivers and flushing DNS cache.",
    "Issue fixed after re-configuring profile and clearing cached credentials.",
    "Access provisioned. User confirmed working.",
    "Driver reinstalled and settings corrected. Tested successfully.",
    "Root cause was a corrupted installation. Repaired successfully.",
    "Credentials reset and role reassigned.",
    "Client reinstalled. Issue was caused by outdated cache files.",
    "Escalated to relevant team and resolved after follow-up.",
]

REJECTION_REASONS = [
    "Ticket raised to wrong department. Please re-raise to IT.",
    "Insufficient information provided. Please add more details and re-submit.",
    "This is a duplicate of an existing ticket.",
    "Issue falls outside our department's scope.",
]


def run_seed():
    db = SessionLocal()
    try:
        existing = db.query(User).count()
        if existing > 0:
            print(f"Seed data already exists ({existing} users found). Skipping.")
            return

        # -----------------------------------------------------------------------
        # Departments
        # -----------------------------------------------------------------------
        dept_names = ["IT", "HR", "Accounts", "Security"]
        dept_title_map = {
            "IT": IT_TITLES,
            "HR": HR_TITLES,
            "Accounts": ACCOUNTS_TITLES,
            "Security": SECURITY_TITLES,
        }
        departments = {}
        for name in dept_names:
            d = Department(name=name)
            db.add(d)
            departments[name] = d

        db.flush()

        # -----------------------------------------------------------------------
        # Admin (no department)
        # -----------------------------------------------------------------------
        admin = User(
            email="admin@opspilot.com",
            hashed_password=hash_password("admin123"),
            full_name="System Admin",
            role=UserRole.ADMIN,
            department_id=None,
            is_active=True,
        )
        db.add(admin)
        db.flush()

        # -----------------------------------------------------------------------
        # Managers and Members per department
        # -----------------------------------------------------------------------
        dept_managers = {}   # dept_name -> list of manager Users
        dept_members = {}    # dept_name -> list of member Users

        for dept_name, dept in departments.items():
            managers = []
            for i in range(2):
                first = fake.first_name()
                last = fake.last_name()
                u = User(
                    email=f"{first.lower()}.{last.lower()}.mgr{i}@opspilot.com",
                    hashed_password=hash_password("password123"),
                    full_name=f"{first} {last}",
                    role=UserRole.MANAGER,
                    department_id=dept.id,
                    is_active=True,
                )
                db.add(u)
                managers.append(u)
            dept_managers[dept_name] = managers

            members = []
            for i in range(4):
                first = fake.first_name()
                last = fake.last_name()
                u = User(
                    email=f"{first.lower()}.{last.lower()}.mem{i}@opspilot.com",
                    hashed_password=hash_password("password123"),
                    full_name=f"{first} {last}",
                    role=UserRole.MEMBER,
                    department_id=dept.id,
                    is_active=True,
                )
                db.add(u)
                members.append(u)
            dept_members[dept_name] = members

        db.flush()

        # Ticket creators — mix of managers and members across all depts
        all_users = [admin]
        for dept_name in dept_names:
            all_users += dept_managers[dept_name]
            all_users += dept_members[dept_name]

        # -----------------------------------------------------------------------
        # Tickets
        # -----------------------------------------------------------------------
        tickets_created = []

        def make_ticket(target_dept_name, status, manager_action, creator, manager, assignee,
                        created_days_ago, rejection_reason=None):
            dept = departments[target_dept_name]
            titles = dept_title_map[target_dept_name]
            is_resolved = status in (TicketStatus.RESOLVED, TicketStatus.CLOSED)
            created_at = datetime.now(timezone.utc) - timedelta(days=created_days_ago)
            resolved_at = created_at + timedelta(hours=random.randint(4, 72)) if is_resolved else None

            t = Ticket(
                title=random.choice(titles),
                description=random.choice(DESCRIPTIONS),
                status=status,
                priority=random.choice(list(TicketPriority)),
                category=random.choice(["Hardware", "Software", "Network", "Access", "Other"]),
                created_by_id=creator.id,
                target_department_id=dept.id,
                manager_id=manager.id if manager else None,
                manager_action=manager_action,
                rejection_reason=rejection_reason,
                assigned_to_id=assignee.id if assignee else None,
                resolution_notes=random.choice(RESOLUTION_NOTES) if is_resolved else None,
                ai_category=random.choice(["Hardware", "Software", "Network", "Access", "Other"]),
                ai_priority=random.choice(["low", "medium", "high", "critical"]),
                ai_summary=fake.sentence(nb_words=12),
                created_at=created_at,
                updated_at=created_at,
                resolved_at=resolved_at,
            )
            db.add(t)
            tickets_created.append(t)

        for dept_name in dept_names:
            managers = dept_managers[dept_name]
            members = dept_members[dept_name]
            creators = [u for u in all_users if u != admin]

            # Pending review — no manager action yet
            for _ in range(5):
                make_ticket(dept_name, TicketStatus.PENDING_REVIEW, ManagerAction.PENDING,
                            random.choice(creators), None, None,
                            random.randint(1, 5))

            # Rejected
            for _ in range(3):
                make_ticket(dept_name, TicketStatus.REJECTED, ManagerAction.REJECTED,
                            random.choice(creators), random.choice(managers), None,
                            random.randint(2, 10),
                            rejection_reason=random.choice(REJECTION_REASONS))

            # Accepted but not yet assigned
            for _ in range(4):
                make_ticket(dept_name, TicketStatus.ACCEPTED, ManagerAction.ACCEPTED,
                            random.choice(creators), random.choice(managers), None,
                            random.randint(1, 7))

            # Assigned
            for _ in range(6):
                make_ticket(dept_name, TicketStatus.ASSIGNED, ManagerAction.ACCEPTED,
                            random.choice(creators), random.choice(managers),
                            random.choice(members), random.randint(3, 15))

            # In progress
            for _ in range(5):
                make_ticket(dept_name, TicketStatus.IN_PROGRESS, ManagerAction.ACCEPTED,
                            random.choice(creators), random.choice(managers),
                            random.choice(members), random.randint(5, 20))

            # Resolved
            for _ in range(6):
                make_ticket(dept_name, TicketStatus.RESOLVED, ManagerAction.ACCEPTED,
                            random.choice(creators), random.choice(managers),
                            random.choice(members), random.randint(10, 60))

            # Closed
            for _ in range(4):
                make_ticket(dept_name, TicketStatus.CLOSED, ManagerAction.ACCEPTED,
                            random.choice(creators), random.choice(managers),
                            random.choice(members), random.randint(20, 90))

        db.flush()

        # -----------------------------------------------------------------------
        # Comments
        # -----------------------------------------------------------------------
        comments_created = 0
        for ticket in tickets_created:
            num_comments = random.randint(0, 4)
            for _ in range(num_comments):
                author = random.choice(all_users)
                comment = TicketComment(
                    ticket_id=ticket.id,
                    author_id=author.id,
                    body=fake.paragraph(nb_sentences=random.randint(1, 3)),
                    is_internal=random.random() < 0.3,
                    created_at=ticket.created_at + timedelta(hours=random.randint(1, 48)),
                )
                db.add(comment)
                comments_created += 1

        db.commit()

        # -----------------------------------------------------------------------
        # Summary
        # -----------------------------------------------------------------------
        print("\n✅ Seed complete!")
        print(f"   Departments : {len(departments)}: {', '.join(dept_names)}")
        print(f"   Admin       : admin@opspilot.com / admin123")
        print(f"   Managers    : 2 per dept x 4 depts = 8 total / password123")
        print(f"   Members     : 4 per dept x 4 depts = 16 total / password123")
        print(f"   Tickets     : {len(tickets_created)}")
        print(f"   Comments    : {comments_created}")
        print("\n   Sample manager logins:")
        for dept_name in dept_names:
            m = dept_managers[dept_name][0]
            print(f"     {dept_name}: {m.email} / password123")

    except Exception as e:
        db.rollback()
        print(f"Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
