"""认证 API 路由（JWT + RBAC）"""

import enum
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header, status
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import User, Role, Department, KnowledgeBasePermission, KnowledgeBase
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 7


# === Pydantic Schemas ===

class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserResponse"


class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
    display_name: str = ""
    role: str = "viewer"
    department_id: Optional[str] = None


class UserUpdate(BaseModel):
    email: Optional[str] = None
    display_name: Optional[str] = None
    role: Optional[str] = None
    department_id: Optional[str] = None
    is_active: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    username: str
    email: Optional[str] = None
    display_name: str = ""
    role: str
    department_id: Optional[str] = None
    is_active: bool = True
    created_at: datetime

    class Config:
        from_attributes = True


class DepartmentCreate(BaseModel):
    name: str
    description: str = ""


class DepartmentResponse(BaseModel):
    id: str
    name: str
    description: str = ""
    created_at: datetime

    class Config:
        from_attributes = True


class KBPermissionRequest(BaseModel):
    user_id: str
    permission: str  # admin / editor / viewer


# === Helpers ===

def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(data: dict) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    authorization: str = Header(default=""),
) -> User:
    """从 Authorization header 中提取 JWT 并返回当前用户。"""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization[7:]
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """要求当前用户是 admin 角色。"""
    if user.role != Role.ADMIN:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


async def require_kb_access(kb_id: str, user: User, db: AsyncSession, level: str = "viewer") -> bool:
    """检查用户是否有知识库访问权限。admin 角色拥有所有访问权限。"""
    if user.role == Role.ADMIN:
        return True
    result = await db.execute(
        select(KnowledgeBasePermission).where(
            KnowledgeBasePermission.kb_id == kb_id,
            KnowledgeBasePermission.user_id == user.id,
        )
    )
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=403, detail="No access to this knowledge base")
    # permission 等级：admin > editor > viewer
    levels = {"admin": 3, "editor": 2, "viewer": 1}
    if levels.get(perm.permission, 0) < levels.get(level, 1):
        raise HTTPException(status_code=403, detail=f"Requires {level} access")
    return True


# === Auth Endpoints ===

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """用户登录，返回 JWT token"""
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")
    token = create_access_token({"sub": user.id, "role": user.role.value if hasattr(user.role, 'value') else user.role})
    return TokenResponse(access_token=token, user=UserResponse.model_validate(user))


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """获取当前用户信息"""
    return UserResponse.model_validate(user)


# === Admin: User Management ===

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """列出所有用户（仅 admin）"""
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    return [UserResponse.model_validate(u) for u in result.scalars()]


@router.post("/users", response_model=UserResponse)
async def create_user(
    req: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """创建用户（仅 admin）"""
    existing = await db.execute(select(User).where(User.username == req.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already exists")
    user = User(
        username=req.username,
        email=req.email,
        password_hash=hash_password(req.password),
        display_name=req.display_name,
        role=Role(req.role),
        department_id=req.department_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    req: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """更新用户信息（仅 admin）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if req.email is not None:
        user.email = req.email
    if req.display_name is not None:
        user.display_name = req.display_name
    if req.role is not None:
        user.role = Role(req.role)
    if req.department_id is not None:
        user.department_id = req.department_id
    if req.is_active is not None:
        user.is_active = req.is_active
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """删除用户（仅 admin）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    await db.delete(user)
    await db.commit()
    return {"status": "deleted"}


# === Admin: Departments ===

@router.get("/departments", response_model=list[DepartmentResponse])
async def list_departments(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """列出所有部门"""
    result = await db.execute(select(Department).order_by(Department.name))
    return [DepartmentResponse.model_validate(d) for d in result.scalars()]


@router.post("/departments", response_model=DepartmentResponse)
async def create_department(
    req: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """创建部门"""
    dept = Department(name=req.name, description=req.description)
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return DepartmentResponse.model_validate(dept)


@router.delete("/departments/{dept_id}")
async def delete_department(
    dept_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """删除部门"""
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    await db.delete(dept)
    await db.commit()
    return {"status": "deleted"}


# === KB Permissions ===

@router.get("/kb/{kb_id}/permissions")
async def list_kb_permissions(
    kb_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """列出知识库的权限设置"""
    result = await db.execute(
        select(KnowledgeBasePermission).where(KnowledgeBasePermission.kb_id == kb_id)
    )
    perms = result.scalars().all()
    return [
        {"id": p.id, "user_id": p.user_id, "permission": p.permission} for p in perms
    ]


@router.post("/kb/{kb_id}/permissions")
async def set_kb_permission(
    kb_id: str,
    req: KBPermissionRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(require_admin),
):
    """设置知识库的用户权限"""
    # 验证知识库存在
    kb_result = await db.execute(select(KnowledgeBase).where(KnowledgeBase.id == kb_id))
    if not kb_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Knowledge base not found")

    # 查找或创建权限
    result = await db.execute(
        select(KnowledgeBasePermission).where(
            KnowledgeBasePermission.kb_id == kb_id,
            KnowledgeBasePermission.user_id == req.user_id,
        )
    )
    perm = result.scalar_one_or_none()
    if perm:
        perm.permission = req.permission
    else:
        perm = KnowledgeBasePermission(
            kb_id=kb_id, user_id=req.user_id, permission=req.permission
        )
        db.add(perm)
    await db.commit()
    return {"status": "ok", "permission": req.permission}


@router.delete("/kb/{kb_id}/permissions/{user_id}")
async def remove_kb_permission(
    kb_id: str,
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_admin),
):
    """移除知识库的用户权限"""
    result = await db.execute(
        select(KnowledgeBasePermission).where(
            KnowledgeBasePermission.kb_id == kb_id,
            KnowledgeBasePermission.user_id == user_id,
        )
    )
    perm = result.scalar_one_or_none()
    if not perm:
        raise HTTPException(status_code=404, detail="Permission not found")
    await db.delete(perm)
    await db.commit()
    return {"status": "deleted"}
