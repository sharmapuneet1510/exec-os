"""Email config, manual send, and HTML preview endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from sqlalchemy.orm import Session

from db.base import SessionLocal
from db.models import EmailConfigORM

router = APIRouter(prefix="/api/email", tags=["email"])


def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_or_create_cfg(db: Session) -> EmailConfigORM:
    cfg = db.query(EmailConfigORM).filter(EmailConfigORM.id == 1).first()
    if not cfg:
        cfg = EmailConfigORM(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


class EmailConfigIn(BaseModel):
    recipient_email: Optional[str] = ""
    smtp_host: Optional[str] = "smtp.gmail.com"
    smtp_port: Optional[int] = 587
    smtp_user: Optional[str] = ""
    smtp_password: Optional[str] = ""
    smtp_mode: Optional[str] = "starttls"
    sod_time: Optional[str] = "08:00"
    eod_time: Optional[str] = "18:00"
    sod_enabled: Optional[bool] = True
    eod_enabled: Optional[bool] = True


@router.get("/config")
def get_config(db: Session = Depends(_db)):
    cfg = _get_or_create_cfg(db)
    return {
        "recipient_email": cfg.recipient_email or "",
        "smtp_host": cfg.smtp_host or "smtp.gmail.com",
        "smtp_port": cfg.smtp_port or 587,
        "smtp_user": cfg.smtp_user or "",
        "smtp_password": "••••••••" if cfg.smtp_password else "",
        "smtp_mode": cfg.smtp_mode or "starttls",
        "sod_time": cfg.sod_time or "08:00",
        "eod_time": cfg.eod_time or "18:00",
        "sod_enabled": cfg.sod_enabled,
        "eod_enabled": cfg.eod_enabled,
    }


@router.post("/config")
def save_config(body: EmailConfigIn, db: Session = Depends(_db)):
    cfg = _get_or_create_cfg(db)
    cfg.recipient_email = body.recipient_email or cfg.recipient_email
    cfg.smtp_host = body.smtp_host or cfg.smtp_host
    cfg.smtp_port = body.smtp_port or cfg.smtp_port
    cfg.smtp_user = body.smtp_user if body.smtp_user is not None else cfg.smtp_user
    if body.smtp_password and body.smtp_password != "••••••••":
        cfg.smtp_password = body.smtp_password
    cfg.smtp_mode = body.smtp_mode or cfg.smtp_mode
    cfg.sod_time = body.sod_time or cfg.sod_time
    cfg.eod_time = body.eod_time or cfg.eod_time
    cfg.sod_enabled = body.sod_enabled
    cfg.eod_enabled = body.eod_enabled
    db.commit()

    try:
        from web import scheduler
        scheduler.reschedule(cfg.sod_time, cfg.eod_time)
    except Exception:
        pass

    return {"ok": True}


@router.post("/send-sod")
def send_sod_now(db: Session = Depends(_db)):
    from web.email_sender import build_sod_html, send_html_email
    cfg = _get_or_create_cfg(db)
    if not cfg.smtp_user or not cfg.recipient_email:
        raise HTTPException(400, "Email not configured — set SMTP credentials and recipient first.")
    try:
        from datetime import date
        html = build_sod_html(db)
        send_html_email(f"📋 Book of Work — {date.today().strftime('%A, %b %d')}", html, cfg)
        return {"ok": True, "message": f"SOD email sent to {cfg.recipient_email}"}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/send-eod")
def send_eod_now(db: Session = Depends(_db)):
    from web.email_sender import build_eod_html, send_html_email
    cfg = _get_or_create_cfg(db)
    if not cfg.smtp_user or not cfg.recipient_email:
        raise HTTPException(400, "Email not configured — set SMTP credentials and recipient first.")
    try:
        from datetime import date
        html = build_eod_html(db)
        send_html_email(f"🌇 Day Summary — {date.today().strftime('%A, %b %d')}", html, cfg)
        return {"ok": True, "message": f"EOD email sent to {cfg.recipient_email}"}
    except Exception as e:
        raise HTTPException(500, str(e))


@router.get("/preview-sod", response_class=HTMLResponse)
def preview_sod(db: Session = Depends(_db)):
    from web.email_sender import build_sod_html
    return build_sod_html(db)


@router.get("/preview-eod", response_class=HTMLResponse)
def preview_eod(db: Session = Depends(_db)):
    from web.email_sender import build_eod_html
    return build_eod_html(db)
