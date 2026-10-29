import os
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database.connection import get_db
from app.models.user import User
from app.models.video import UserVideo
from app.services.auth import get_current_user
from app.utils.datetime_utils import to_utc_iso

router = APIRouter(prefix="/videos", tags=["Video Upload & Library"])

_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.abspath(os.path.join(_current_dir, "..", "..", ".."))
VIDEO_UPLOAD_DIR = os.getenv("VIDEO_UPLOAD_DIR", os.path.join(_project_root, "uploads", "videos"))
os.makedirs(VIDEO_UPLOAD_DIR, exist_ok=True)

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}
MAX_VIDEO_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB


@router.post("/upload", status_code=status.HTTP_201_CREATED)
async def upload_user_video(
    title: str = Form(..., min_length=1, max_length=256),
    video_date: str = Form(...),
    description: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Uploads a personal health or exercise video (MP4, WebM, MOV) with validation."""
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported video format '{ext}'. Supported formats are: MP4, WebM, MOV."
        )

    file_bytes = await file.read()
    file_size = len(file_bytes)
    if file_size > MAX_VIDEO_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Video file exceeds the 100 MB limit."
        )

    safe_name = f"{current_user.id}_{int(datetime.now().timestamp())}_{file.filename}"
    file_path = os.path.join(VIDEO_UPLOAD_DIR, safe_name)
    with open(file_path, "wb") as f:
        f.write(file_bytes)

    video = UserVideo(
        user_id=current_user.id,
        patient_id=current_user.patient_id,
        title=title.strip(),
        video_date=video_date.strip(),
        file_name=file.filename,
        file_path=file_path,
        file_type=ext.replace(".", ""),
        file_size_bytes=file_size,
        description=description.strip() if description else None
    )
    db.add(video)
    db.commit()
    db.refresh(video)

    return {
        "success": True,
        "message": "Video uploaded successfully to your personal health library.",
        "video": {
            "id": video.id,
            "title": video.title,
            "video_date": video.video_date,
            "file_name": video.file_name,
            "file_type": video.file_type,
            "file_size_bytes": video.file_size_bytes,
            "description": video.description,
            "created_at": to_utc_iso(video.created_at)
        }
    }


@router.get("", include_in_schema=True)
@router.get("/", include_in_schema=False)
def list_user_videos(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists all uploaded videos for the authenticated user."""
    videos = db.query(UserVideo).filter(
        UserVideo.user_id == current_user.id
    ).order_by(UserVideo.video_date.desc(), UserVideo.created_at.desc()).all()

    return [
        {
            "id": v.id,
            "title": v.title,
            "video_date": v.video_date,
            "file_name": v.file_name,
            "file_type": v.file_type,
            "file_size_bytes": v.file_size_bytes,
            "description": v.description,
            "stream_url": f"/api/videos/{v.id}/stream",
            "created_at": to_utc_iso(v.created_at)
        }
        for v in videos
    ]


@router.get("/{video_id}/stream")
def stream_user_video(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Streams or serves the video file for HTML5 in-browser playback."""
    video = db.query(UserVideo).filter(
        UserVideo.id == video_id,
        UserVideo.user_id == current_user.id
    ).first()
    if not video or not os.path.exists(video.file_path):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found.")

    mime_map = {
        "mp4": "video/mp4",
        "webm": "video/webm",
        "mov": "video/quicktime"
    }
    media_type = mime_map.get(video.file_type, "video/mp4")

    return FileResponse(
        path=video.file_path,
        media_type=media_type,
        filename=video.file_name
    )


@router.delete("/{video_id}")
def delete_user_video(
    video_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deletes a video record and removes the physical video file."""
    video = db.query(UserVideo).filter(
        UserVideo.id == video_id,
        UserVideo.user_id == current_user.id
    ).first()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found.")

    if os.path.exists(video.file_path):
        try:
            os.remove(video.file_path)
        except Exception:
            pass

    db.delete(video)
    db.commit()
    return {"success": True, "message": "Video deleted successfully."}

