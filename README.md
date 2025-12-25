# Daily Inspection (DI) Platform

A comprehensive web-based Daily Inspection management system for datacenter operations, featuring role-based access control, real-time notifications, workflow management, and equipment tracking.

## ✨ Features

- **Daily Inspection Management**: Structured forms for equipment inspection with status tracking
- **Workflow System**: Multi-level approval workflow (Operator → OIC Elect → OIC Datashell → CDO)
- **Role-Based Access Control (RBAC)**: Multi-role support with granular permissions
- **Real-Time Notifications**: WebSocket-based alerts with Redis pub/sub
- **Equipment Management**: Track equipment status, location, and maintenance history
- **User Management**: Profile management, role assignment, and password reset
- **Audit Logging**: Comprehensive activity tracking for compliance
- **Responsive UI**: Modern glassmorphism design with Tailwind CSS
- **Offline-First**: Works without internet connectivity

## 🛠 Tech Stack

- **Backend**: FastAPI (Python 3.13)
- **Database**: PostgreSQL 15
- **Cache/PubSub**: Redis 7
- **ORM**: SQLAlchemy
- **Authentication**: JWT with Argon2 password hashing
- **Frontend**: Jinja2 templates, Tailwind CSS, Chart.js
- **Deployment**: Docker & Docker Compose

## 🚀 Quick Start

### Using Docker (Recommended)

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd di_app
   ```

2. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env and set your SECRET_KEY and passwords
   ```

3. **Start the application**
   
   **Option A: Full stack (PostgreSQL + Redis + App)**
   ```bash
   docker-compose up -d
   ```
   
   **Option B: App only (use existing local PostgreSQL & Redis)**
   ```bash
   # Ensure your local PostgreSQL and Redis are running
   docker-compose -f docker-compose.local.yml up -d
   ```

4. **Access the application**
   - Open http://localhost:8000
   - Default credentials will be created on first run

### Manual Setup

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed manual installation instructions.

## 📋 Environment Variables

Key environment variables (see `.env.example` for complete list):

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT secret key (REQUIRED in production) | Auto-generated |
| `POSTGRES_HOST` | PostgreSQL host | localhost |
| `POSTGRES_PORT` | PostgreSQL port | 5432 |
| `POSTGRES_USER` | Database user | di_user |
| `POSTGRES_PASSWORD` | Database password | (required) |
| `POSTGRES_DB` | Database name | di_database |
| `REDIS_URL` | Redis connection URL | redis://localhost:6379/0 |

## 📖 Usage

### First-Time Setup

1. **Create Admin User**: The first registered user automatically becomes a sysadmin
2. **Configure Roles**: Navigate to `/roles` to set up additional roles
3. **Add Equipment**: Set up locations (`/places`) and equipment (`/equipments`)
4. **Assign Users**: Create user accounts and assign appropriate roles

### Daily Operations

1. **Submit Inspection**: Navigate to `/di/form` to submit daily inspection
2. **Review Workflow**: Authorized personnel can approve/reject at `/di/tracking`
3. **View History**: Access past inspections at `/di/list`
4. **Monitor Dashboard**: Real-time status overview at `/dashboard`

## 🔐 Default Roles

- **Sysadmin**: Full system access
- **Admin**: User and equipment management
- **CDO**: Final approval authority
- **OIC Datashell**: Mid-level reviewer
- **OIC Elect**: Initial reviewer
- **Operator**: Submit inspections
- **User**: Basic access

## 🏗 Project Structure

```
di_app/
├── app/
│   ├── core/           # Security, auth, notifications
│   ├── db/             # Database configuration
│   ├── models/         # SQLAlchemy models
│   ├── routes/         # API endpoints
│   ├── static/         # CSS, JS, images
│   └── templates/      # Jinja2 HTML templates
├── migrations/         # Database migrations
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## 🔧 Development

### Prerequisites

- Python 3.13+
- PostgreSQL 15+
- Redis 7+

### Setup Development Environment

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up database
# (Ensure PostgreSQL is running)
python migrations/add_full_name.py  # Run any pending migrations

# Start development server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

## 📝 API Documentation

Once the application is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is proprietary software. All rights reserved.

## 🆘 Support

For issues and questions:
- Check [DEPLOYMENT.md](DEPLOYMENT.md) for troubleshooting
- Review the user manual at `/user_manual`
- Contact the development team

## 🔄 Updates

### Recent Changes
- ✅ Multi-role support with role switching
- ✅ Full name vs username separation
- ✅ Enhanced user management
- ✅ Profile picture uploads
- ✅ Role handover functionality
- ✅ Docker deployment support

---

**Built with ❤️ for Datacenter Operations**
