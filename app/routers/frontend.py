from fastapi import APIRouter, Request, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Определяем базовую директорию проекта
BASE_DIR = Path(__file__).parent.parent.parent

# Инициализируем Jinja2Templates
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter(tags=["Frontend"])


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """
    Страница входа в систему.
    """
    return templates.TemplateResponse("login.html", {"request": request})


@router.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    """
    Главная страница (защищенная).
    """
    # Простая HTML страница для главной
    html_content = """
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Главная - УТЗ</title>
        <script src="/static/js/auth.js"></script>
        <style>
            * {
                margin: 0;
                padding: 0;
                box-sizing: border-box;
            }
            
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                background: #f5f5f5;
                min-height: 100vh;
            }
            
            .header {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                color: white;
                padding: 20px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            
            .header-content {
                max-width: 1200px;
                margin: 0 auto;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .header h1 {
                font-size: 24px;
            }
            
            .user-info {
                display: flex;
                align-items: center;
                gap: 20px;
            }
            
            .btn-logout {
                background: rgba(255,255,255,0.2);
                color: white;
                border: 1px solid rgba(255,255,255,0.3);
                padding: 8px 16px;
                border-radius: 5px;
                cursor: pointer;
                transition: background 0.3s;
            }
            
            .btn-logout:hover {
                background: rgba(255,255,255,0.3);
            }
            
            .container {
                max-width: 1200px;
                margin: 40px auto;
                padding: 20px;
            }
            
            .welcome-card {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            
            .welcome-card h2 {
                color: #333;
                margin-bottom: 20px;
            }
            
            .user-details {
                background: #f9f9f9;
                padding: 20px;
                border-radius: 5px;
                margin-top: 20px;
            }
            
            .user-details p {
                margin: 10px 0;
                color: #666;
            }
            
            .user-details strong {
                color: #333;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <div class="header-content">
                <h1>🏢 УТЗ - Журнал регистрации номеров КД</h1>
                <div class="user-info">
                    <span id="userName">Пользователь</span>
                    <button class="btn-logout" onclick="logout()">Выйти</button>
                </div>
            </div>
        </div>
        
        <div class="container">
            <div class="welcome-card">
                <h2>Добро пожаловать!</h2>
                <p>Вы успешно вошли в систему.</p>
                
                <div class="user-details" id="userDetails">
                    <p><strong>Загрузка информации...</strong></p>
                </div>
            </div>
        </div>
        
        <script>
            // Загружаем информацию о пользователе
            document.addEventListener('DOMContentLoaded', async () => {
                const user = getCurrentUser();
                if (user) {
                    document.getElementById('userName').textContent = user.full_name || user.username;
                    
                    const userDetails = document.getElementById('userDetails');
                    userDetails.innerHTML = `
                        <p><strong>Имя пользователя:</strong> ${user.username}</p>
                        <p><strong>Полное имя:</strong> ${user.full_name || 'Не указано'}</p>
                        <p><strong>Email:</strong> ${user.email || 'Не указан'}</p>
                        <p><strong>Группы:</strong> ${user.groups ? user.groups.join(', ') : 'Нет групп'}</p>
                        <p><strong>Статус:</strong> ${user.is_active ? 'Активен' : 'Неактивен'}</p>
                    `;
                } else {
                    // Если нет информации, получаем с сервера
                    try {
                        const response = await fetch('/auth/me');
                        if (response.ok) {
                            const userData = await response.json();
                            localStorage.setItem('user_info', JSON.stringify(userData));
                            document.getElementById('userName').textContent = userData.full_name || userData.username;
                            
                            const userDetails = document.getElementById('userDetails');
                            userDetails.innerHTML = `
                                <p><strong>Имя пользователя:</strong> ${userData.username}</p>
                                <p><strong>Полное имя:</strong> ${userData.full_name || 'Не указано'}</p>
                                <p><strong>Email:</strong> ${userData.email || 'Не указан'}</p>
                                <p><strong>Группы:</strong> ${userData.groups ? userData.groups.join(', ') : 'Нет групп'}</p>
                                <p><strong>Статус:</strong> ${userData.is_active ? 'Активен' : 'Неактивен'}</p>
                            `;
                        }
                    } catch (error) {
                        console.error('Error fetching user data:', error);
                    }
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

