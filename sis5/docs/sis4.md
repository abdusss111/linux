Abdurakhimov Abdussalam Information Systems  SIS4  Topic: Working with services Target: Create and configure Linux services, Containers and scheduled scripts.
1. Docker Images
Created two Docker images for the 2-VM Dapmeet architecture:
   
[Screenshot 1: VM1 and VM2  Dockerfiles]
[Screenshot 2: Docker Hub - frontend and backend repos]
 
Docker Hub Links: 
https://hub.docker.com/repository/docker/abdusss111/dapmeet-client/
https://hub.docker.com/repository/docker/abdusss111/dapmeet-service

2. Systemd Services
Created systemd unit files for both containers with automatic restart capability 
 
 

3. Scheduled Tasks
Created 4 scripts scheduled via cron for automated maintenance on both VMs.
VM1 - Frontend Scripts
 
VM2 - Backend Scripts
 

Conclusions
Successfully completed all TSis #4 tasks for the 2-VM Dapmeet architecture:
1. Created and published 2 Docker images (frontend and backend) to Docker Hub with health checks and proper configuration.
2. Configured 2 systemd services (one per VM) for automated container management with auto-restart on failure.
3. Implemented 4 scheduled scripts via cron for backup and maintenance automation on both VMs.
Key learning outcomes:
• Multi-server Docker containerization and orchestration
• Systemd service management across distributed systems
• Automated backup and maintenance workflows
• Cron-based task scheduling for system automation
