Abdurakhimov Abdussalam
Information Systems
SIS1 
Topic: Project introduction, machines provisioning
Target: Create a clear definition of the individual project, create an architecture of the system and prepare machine(s) for it.
1. Choose and describe project
Dapmeet - service for transcribing Google Meet online meetings, getting summary from them, chat with AI, ask anything about meeting from chat
2. Create an architecture of your project.
Server Infrastructure
1. Frontend Hosting Server (Vercel current setup - for this course move to VM in Cloud or self-hosted)
Purpose: Hosts all client-side applications
Applications Deployed:
●	Landing Page
●	Admin Panel
●	Main Frontend Application
●	Extension in Chrome Web Store
Key Software/Technologies:
●	Node.js runtime environment
●	Next.js framework
●	Static file serving capabilities
●	CDN integration for global content delivery
●	SSL/TLS certificates for HTTPS
●	Git integration for automated deployments
2. Backend Application Server (Render)
Purpose: Handles business logic, API endpoints, and server-side processing
Key Software Installed:
●	Runtime environment (Python, Docker)
●	Web framework (FastAPI)
●	Logging and monitoring tools
3. Database Server (Render)
Purpose: Data storage and management
Key Software Installed:
●	Database management system (PostgreSQL)
●	Database connection pooling
●	Backup and recovery tools
●	Database monitoring utilities
Application Components
1. Landing Page
●	Platform: Vercel
●	Function: Marketing/promotional website entry point
●	Technologies: Static site generation, responsive design frameworks
2. Admin Panel
●	Platform: Vercel
●	Function: Administrative interface for system management
●	Technologies: Admin dashboard framework, authentication integration
3. Main Frontend
●	Platform: Vercel
●	Function: Primary user interface for the application
●	Technologies: Frontend framework Next.js, state management,Shadcn UI libraries
4. Backend API
●	Platform: Render
●	Function: Server-side logic, data processing, API services
●	Technologies: RESTful API framework, authentication services, business logic processors
5. Database
●	Platform: Render
●	Function: Persistent data storage
●	Technologies: Relational/NoSQL database, indexing, query optimization



3. Prepare machines for your project
If i will get approve from my company to move to Yandex Cloud Infra i will do it
If not i already have Virtual Machine on my own laptop, issue 2 VMs on Ubuntu. 1 for presentation layer, 1 for backend & database
4. Define places of storing data and configurations
a) Where do users store their data? 
	User Data Storage
●	Primary Location: PostgreSQL Database on Render/VM
●	Path: /var/lib/postgresql/14/main/ (if self-hosted)
Tables:
●	users - User accounts and authentication data
●	meetings - Meeting metadata (title, date, duration, participants)
●	transcriptions - Raw transcription text and timestamps
●	summaries - AI-generated meeting summaries
●	chat_sessions - User interactions with AI chat
●	user_settings - Personal preferences and configurations
b) Where do pieces of software (db/services) store data?
Backend Service (FastAPI)
●	Application Data: PostgreSQL database
●	Logs: ./logs/segment_batches.jsonl
Frontend Applications (Next.js)
●	Static Assets: Vercel CDN or /var/www/dapmeet/static/
●	Build Output: /.next/ directory
●	Client Cache: Browser localStorage and sessionStorage
●	Logs: Vercel analytics or /var/log/nginx/dapmeet_access.log
Database (PostgreSQL)
●	Data Files: /var/lib/postgresql/14/main/
●	WAL Files: /var/lib/postgresql/14/main/pg_wal/
●	Backups: /var/backups/dapmeet/postgresql/
●	Configuration: /etc/postgresql/14/main/postgresql.conf
Chrome Extension
●	Chrome Storage: Chrome extension local storage API
●	Cached Data: Chrome extension cache
●	User Preferences: Extension sync storage

c) Where do you store config files for each piece of software?
Backend Configuration
●	/opt/dapmeet/backend/
●	├── .env                          # Environment variables
●	├── pyproject.toml               # Python project configuration
●	├── requirements.txt             # Python dependencies
●	├── alembic.ini                  # Database migration configuration
●	└── config/
●	    ├── database.conf            # Database connection settings
●	    ├── logging.conf             # Logging configuration
●	    └── security.conf            # Security and JWT settings

Frontend Configuration
●	/opt/dapmeet/frontend/
●	├── .env.local                   # Local environment variables
●	├── .env.production              # Production environment variables
●	├── next.config.js               # Next.js configuration
●	├── package.json                 # Node.js dependencies
●	├── tailwind.config.js           # Tailwind CSS configuration
●	└── tsconfig.json                # TypeScript configuration
System Configuration
●	/etc/dapmeet/
●	├── nginx/
●	│   ├── sites-available/dapmeet  # Nginx virtual host
●	│   └── ssl/                     # SSL certificates
●	├── systemd/
●	│   ├── dapmeet-backend.service  # Backend service configuration
●	│   └── dapmeet-worker.service   # Background worker service
●	└── logrotate.d/dapmeet          # Log rotation configuration

d) In what format are config files?
●	Environment Variables: .env format (KEY=value)
●	Python Configuration: pyproject.toml format (TOML)
●	JavaScript/Node.js: package.json (JSON), .js config files
●	Database: .conf format (PostgreSQL configuration syntax)
●	Web Server: Nginx configuration format
●	System Services: systemd unit file format
User Data: PostgreSQL database storing meetings, transcriptions, summaries, and user data
Configuration Storage:
●	Backend: /opt/dapmeet/backend/ (.env, pyproject.toml files)
●	Frontend: /opt/dapmeet/frontend/ (.env, next.config.js files)
●	System: /etc/dapmeet/ (nginx, systemd configs)
Key Directories:
●	/opt/dapmeet/ - Main application files
●	/var/dapmeet/ - Runtime data and processed files
●	/var/log/dapmeet/ - Application logs
●	/tmp/dapmeet-setup/ - Temporary setup automation files
Formats: .env (environment variables), .toml (Python config), .json/.js (Node.js config), .conf (system configs)
Backup Locations: /var/backups/dapmeet/ for database, config, and application backups



