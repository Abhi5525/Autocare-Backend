"""
Script to approve all pending services - one-time cleanup
"""
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from app.core.database import engine
from app.models.service import ServiceRecord, ServiceStatus
from datetime import datetime

def approve_pending_services():
    """Approve all pending services"""
    with Session(engine) as session:
        # Get all pending approval services
        statement = select(ServiceRecord).where(
            ServiceRecord.status == ServiceStatus.PENDING_APPROVAL
        )
        pending_services = session.exec(statement).all()
        
        if not pending_services:
            print("✓ No pending services found")
            return
        
        print(f"Found {len(pending_services)} pending service(s)")
        
        for service in pending_services:
            print(f"  - Approving service ID {service.id}...")
            service.status = ServiceStatus.APPROVED
            service.approved_at = datetime.now()
            service.updated_at = datetime.now()
            # Set approver to mechanic who created it
            if service.mechanic_id and not service.approver_id:
                service.approver_id = service.mechanic_id
            session.add(service)
        
        session.commit()
        print(f"\n✓ Successfully approved {len(pending_services)} service(s)!")

if __name__ == "__main__":
    try:
        approve_pending_services()
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
