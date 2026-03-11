import logging
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import func

import models
import schemas
from dependencies import get_db, get_current_user, get_current_user_optional

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/community", tags=["community"])

VALID_POST_TYPES = {"backtest_share", "performance_share", "strategy_review", "discussion"}


def _post_to_response(post: models.CommunityPost, current_user_id: Optional[int], db: Session) -> schemas.PostResponse:
    liked = False
    if current_user_id is not None:
        liked = db.query(models.PostLike).filter(
            models.PostLike.post_id == post.id,
            models.PostLike.user_id == current_user_id,
        ).first() is not None

    return schemas.PostResponse(
        id=post.id,
        user_id=post.user_id,
        author_nickname=post.author.nickname if post.author else None,
        post_type=post.post_type,
        title=post.title,
        content=post.content,
        backtest_data=json.loads(post.backtest_data) if post.backtest_data else None,
        performance_data=json.loads(post.performance_data) if post.performance_data else None,
        strategy_name=post.strategy_name,
        timeframe=post.timeframe,
        rating=post.rating,
        like_count=post.like_count,
        comment_count=post.comment_count,
        is_liked=liked,
        created_at=post.created_at,
    )


# -------- Profile --------

@router.put("/profile/nickname", response_model=schemas.UserProfileResponse)
async def update_nickname(
    body: schemas.NicknameUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    nickname = body.nickname.strip()
    if len(nickname) < 2 or len(nickname) > 20:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="닉네임은 2자 이상 20자 이하여야 합니다.",
        )

    existing = db.query(models.User).filter(
        models.User.nickname == nickname,
        models.User.id != current_user.id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 사용 중인 닉네임입니다.",
        )

    current_user.nickname = nickname
    db.commit()
    db.refresh(current_user)

    post_count = db.query(models.CommunityPost).filter(
        models.CommunityPost.user_id == current_user.id,
        models.CommunityPost.is_deleted == False,
    ).count()

    return schemas.UserProfileResponse(
        id=current_user.id,
        nickname=current_user.nickname,
        email=current_user.email,
        created_at=current_user.created_at,
        post_count=post_count,
    )


@router.get("/profile/{user_id}", response_model=schemas.UserProfileResponse)
async def get_user_profile(
    user_id: int,
    db: Session = Depends(get_db),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="사용자를 찾을 수 없습니다.")

    post_count = db.query(models.CommunityPost).filter(
        models.CommunityPost.user_id == user_id,
        models.CommunityPost.is_deleted == False,
    ).count()

    return schemas.UserProfileResponse(
        id=user.id,
        nickname=user.nickname,
        email=user.email,
        created_at=user.created_at,
        post_count=post_count,
    )


# -------- Posts --------

@router.get("/posts", response_model=schemas.PostListResponse)
async def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    post_type: Optional[str] = Query(None),
    current_user: Optional[models.User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    query = db.query(models.CommunityPost).filter(models.CommunityPost.is_deleted == False)

    if post_type:
        if post_type not in VALID_POST_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"유효하지 않은 post_type입니다. 허용: {', '.join(VALID_POST_TYPES)}",
            )
        query = query.filter(models.CommunityPost.post_type == post_type)

    total = query.count()
    posts = (
        query.order_by(models.CommunityPost.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    user_id = current_user.id if current_user else None
    post_responses = [_post_to_response(p, user_id, db) for p in posts]

    return schemas.PostListResponse(
        posts=post_responses,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/posts", response_model=schemas.PostResponse, status_code=status.HTTP_201_CREATED)
async def create_post(
    body: schemas.PostCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.post_type not in VALID_POST_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"유효하지 않은 post_type입니다. 허용: {', '.join(VALID_POST_TYPES)}",
        )

    if not body.title or not body.title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="제목은 필수입니다.")

    if body.post_type == "strategy_review":
        if not body.strategy_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="전략 리뷰에는 strategy_name이 필수입니다.",
            )
        if body.rating is not None and (body.rating < 1 or body.rating > 5):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="평점은 1에서 5 사이여야 합니다.",
            )

    post = models.CommunityPost(
        user_id=current_user.id,
        post_type=body.post_type,
        title=body.title.strip(),
        content=body.content,
        backtest_data=json.dumps(body.backtest_data) if body.backtest_data else None,
        performance_data=json.dumps(body.performance_data) if body.performance_data else None,
        strategy_name=body.strategy_name,
        timeframe=body.timeframe,
        rating=body.rating,
    )
    db.add(post)
    db.commit()
    db.refresh(post)

    logger.info("User %d created post %d (type=%s)", current_user.id, post.id, post.post_type)
    return _post_to_response(post, current_user.id, db)


@router.get("/posts/{post_id}", response_model=schemas.PostResponse)
async def get_post(
    post_id: int,
    current_user: Optional[models.User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    post = db.query(models.CommunityPost).filter(
        models.CommunityPost.id == post_id,
        models.CommunityPost.is_deleted == False,
    ).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다.")
    user_id = current_user.id if current_user else None
    return _post_to_response(post, user_id, db)


@router.put("/posts/{post_id}", response_model=schemas.PostResponse)
async def update_post(
    post_id: int,
    body: schemas.PostCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(models.CommunityPost).filter(
        models.CommunityPost.id == post_id,
        models.CommunityPost.is_deleted == False,
    ).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다.")

    if post.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="본인의 게시글만 수정할 수 있습니다.")

    if not body.title or not body.title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="제목은 필수입니다.")

    if body.post_type == "strategy_review":
        if not body.strategy_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="전략 리뷰에는 strategy_name이 필수입니다.",
            )
        if body.rating is not None and (body.rating < 1 or body.rating > 5):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="평점은 1에서 5 사이여야 합니다.",
            )

    post.post_type = body.post_type
    post.title = body.title.strip()
    post.content = body.content
    post.backtest_data = json.dumps(body.backtest_data) if body.backtest_data else None
    post.performance_data = json.dumps(body.performance_data) if body.performance_data else None
    post.strategy_name = body.strategy_name
    post.timeframe = body.timeframe
    post.rating = body.rating
    db.commit()
    db.refresh(post)

    logger.info("User %d updated post %d", current_user.id, post.id)
    return _post_to_response(post, current_user.id, db)


@router.delete("/posts/{post_id}")
async def delete_post(
    post_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(models.CommunityPost).filter(
        models.CommunityPost.id == post_id,
        models.CommunityPost.is_deleted == False,
    ).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다.")

    if post.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="본인의 게시글만 삭제할 수 있습니다.")

    post.is_deleted = True
    db.commit()

    logger.info("User %d soft-deleted post %d", current_user.id, post_id)
    return {"detail": "게시글이 삭제되었습니다."}


# -------- Likes --------

@router.post("/posts/{post_id}/like")
async def toggle_like(
    post_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(models.CommunityPost).filter(
        models.CommunityPost.id == post_id,
        models.CommunityPost.is_deleted == False,
    ).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다.")

    existing_like = db.query(models.PostLike).filter(
        models.PostLike.post_id == post_id,
        models.PostLike.user_id == current_user.id,
    ).first()

    if existing_like:
        db.delete(existing_like)
        post.like_count = max(0, post.like_count - 1)
        db.commit()
        return {"liked": False, "like_count": post.like_count}
    else:
        new_like = models.PostLike(post_id=post_id, user_id=current_user.id)
        db.add(new_like)
        post.like_count = post.like_count + 1
        db.commit()
        return {"liked": True, "like_count": post.like_count}


# -------- Comments --------

@router.get("/posts/{post_id}/comments", response_model=list[schemas.CommentResponse])
async def list_comments(
    post_id: int,
    db: Session = Depends(get_db),
):
    post = db.query(models.CommunityPost).filter(
        models.CommunityPost.id == post_id,
        models.CommunityPost.is_deleted == False,
    ).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다.")

    comments = (
        db.query(models.PostComment)
        .filter(
            models.PostComment.post_id == post_id,
            models.PostComment.is_deleted == False,
        )
        .order_by(models.PostComment.created_at.asc())
        .all()
    )

    return [
        schemas.CommentResponse(
            id=c.id,
            user_id=c.user_id,
            author_nickname=c.author.nickname if c.author else None,
            content=c.content,
            created_at=c.created_at,
        )
        for c in comments
    ]


@router.post("/posts/{post_id}/comments", response_model=schemas.CommentResponse, status_code=status.HTTP_201_CREATED)
async def create_comment(
    post_id: int,
    body: schemas.CommentCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    post = db.query(models.CommunityPost).filter(
        models.CommunityPost.id == post_id,
        models.CommunityPost.is_deleted == False,
    ).first()
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="게시글을 찾을 수 없습니다.")

    if not body.content or not body.content.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="댓글 내용은 필수입니다.")

    comment = models.PostComment(
        post_id=post_id,
        user_id=current_user.id,
        content=body.content.strip(),
    )
    db.add(comment)
    post.comment_count = post.comment_count + 1
    db.commit()
    db.refresh(comment)

    logger.info("User %d commented on post %d", current_user.id, post_id)
    return schemas.CommentResponse(
        id=comment.id,
        user_id=comment.user_id,
        author_nickname=current_user.nickname,
        content=comment.content,
        created_at=comment.created_at,
    )


@router.delete("/comments/{comment_id}")
async def delete_comment(
    comment_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    comment = db.query(models.PostComment).filter(
        models.PostComment.id == comment_id,
        models.PostComment.is_deleted == False,
    ).first()
    if not comment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="댓글을 찾을 수 없습니다.")

    if comment.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="본인의 댓글만 삭제할 수 있습니다.")

    comment.is_deleted = True

    post = db.query(models.CommunityPost).filter(models.CommunityPost.id == comment.post_id).first()
    if post:
        post.comment_count = max(0, post.comment_count - 1)

    db.commit()

    logger.info("User %d deleted comment %d", current_user.id, comment_id)
    return {"detail": "댓글이 삭제되었습니다."}


# -------- Chat --------

@router.get("/chat", response_model=list[schemas.ChatMessageResponse])
async def get_chat_messages(
    after_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(models.ChatMessage)

    if after_id is not None:
        query = query.filter(models.ChatMessage.id > after_id)

    messages = query.order_by(models.ChatMessage.created_at.asc()).limit(50).all()

    return [
        schemas.ChatMessageResponse(
            id=m.id,
            user_id=m.user_id,
            author_nickname=m.author.nickname if m.author else None,
            content=m.content,
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.post("/chat", response_model=schemas.ChatMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_chat_message(
    body: schemas.ChatMessageCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not body.content or not body.content.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="메시지 내용은 필수입니다.")

    content = body.content.strip()
    if len(content) > 500:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="메시지는 500자 이하여야 합니다.")

    message = models.ChatMessage(
        user_id=current_user.id,
        content=content,
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return schemas.ChatMessageResponse(
        id=message.id,
        user_id=message.user_id,
        author_nickname=current_user.nickname,
        content=message.content,
        created_at=message.created_at,
    )


# -------- Strategy Reviews --------

@router.get("/strategies/{strategy_name}/reviews", response_model=list[schemas.PostResponse])
async def get_strategy_reviews(
    strategy_name: str,
    timeframe: Optional[str] = Query(None),
    current_user: Optional[models.User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    query = (
        db.query(models.CommunityPost)
        .filter(
            models.CommunityPost.post_type == "strategy_review",
            models.CommunityPost.strategy_name == strategy_name,
            models.CommunityPost.is_deleted == False,
        )
    )

    if timeframe:
        query = query.filter(models.CommunityPost.timeframe == timeframe)

    posts = query.order_by(models.CommunityPost.created_at.desc()).all()

    user_id = current_user.id if current_user else None
    return [_post_to_response(p, user_id, db) for p in posts]


@router.get("/strategies/{strategy_name}/rating")
async def get_strategy_rating(
    strategy_name: str,
    db: Session = Depends(get_db),
):
    result = (
        db.query(
            func.avg(models.CommunityPost.rating).label("average_rating"),
            func.count(models.CommunityPost.id).label("review_count"),
        )
        .filter(
            models.CommunityPost.post_type == "strategy_review",
            models.CommunityPost.strategy_name == strategy_name,
            models.CommunityPost.rating.isnot(None),
            models.CommunityPost.is_deleted == False,
        )
        .first()
    )

    avg_rating = round(float(result.average_rating), 2) if result.average_rating else None
    review_count = result.review_count or 0

    return {
        "strategy_name": strategy_name,
        "average_rating": avg_rating,
        "review_count": review_count,
    }
