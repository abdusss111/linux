Abdurakhimov Abdussalam 
Information Systems 
SIS1  
Topic: Users and permissions
Target: Define a role table and prepare automation of the setup.
1.	 Declare a role table
a) What roles/groups of users will be in your system?
Service Groups:
●	postgres -> users: postgres, dba_user, backup
●	www-data -> users: nginx
●	dapmeet -> users: dapmeet-backend, dapmeet-worker, devops_user, automation, deployer
Administrative Groups:
●	sudo -> users: sysadmin
●	sysadmin -> users: sysadmin
●	devops -> users: devops_user
●	dba -> users: dba_user
●	docker -> users: devops_user (if Docker is used)
Service Groups:
●	automation -> users: automation
●	monitoring -> users: monitoring
●	backup -> users: backup
●	auditor -> users: auditor
●	deployer -> users: deployer
b) What permissions will be for each role/group?
c) What of super user permissions need to be added to each role/group?





Role Name	Description	Primary Group	Secondary Groups	Standard Permissions	Superuser (sudo) Permissions	Shell	SSH Access	Location	Type
postgres	PostgreSQL database service	postgres	-	  Owner: /var/lib/postgresql/14/main/, /var/lib/postgresql/14/main/pg_wal/   R/W: /var/backups/dapmeet/postgresql/   Read: /etc/postgresql/14/main/   Execute: /usr/lib/postgresql/14/bin/postgres	None	/bin/bash	No	VM2	Server
nginx	Nginx web server	www-data	-	  Read: /opt/dapmeet/frontend/, /var/www/dapmeet/static/   Owner: /var/log/nginx/dapmeet_*.log   Read: /etc/dapmeet/nginx/, /etc/dapmeet/ssl/	None	/usr/sbin/nologin	No	VM1	Server
dapmeet-backend	FastAPI backend service	dapmeet	-	  Owner: /opt/dapmeet/backend/, /var/dapmeet/, /var/log/dapmeet/backend.log   R/W: /tmp/dapmeet-setup/   Read: /opt/dapmeet/backend/.env, /etc/dapmeet/backend/	None	/bin/bash	No	VM2	Server
dapmeet-worker	Background worker for transcriptions	dapmeet	-	  R/W: /var/dapmeet/processing/   Owner: /var/log/dapmeet/worker.log   Read: /opt/dapmeet/backend/, /etc/dapmeet/backend/	None	/bin/bash	No	VM2	Server
sysadmin	System administrator	sysadmin	sudo	  R/W: All /etc/, /opt/dapmeet/, /var/log/dapmeet/   Manage all systemd services   Full system access	ALL=(ALL:ALL) ALL	/bin/bash	Yes (key)	VM1, VM2	Client
devops_user	DevOps engineer	devops	dapmeet, docker	  R/W: /opt/dapmeet/   Read: /etc/dapmeet/, /var/log/dapmeet/   Docker management	%devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dapmeet-* %devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl status dapmeet-* %devops ALL=(ALL) NOPASSWD: /usr/bin/systemctl stop dapmeet-* %devops ALL=(ALL) /usr/sbin/nginx -t %devops ALL=(ALL) /usr/bin/docker *	/bin/bash	Yes (key)	VM1, VM2	Client
dba_user	Database administrator	dba	postgres	  R/W: /var/lib/postgresql/, /var/backups/dapmeet/postgresql/, /etc/postgresql/   Execute: psql, pg_dump, pg_restore	%dba ALL=(postgres) NOPASSWD: /usr/bin/psql %dba ALL=(postgres) NOPASSWD: /usr/bin/pg_dump %dba ALL=(postgres) NOPASSWD: /usr/bin/pg_restore %dba ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart postgresql	/bin/bash	Yes (key)	VM2	Client
automation	CI/CD automation bot	automation	dapmeet	  R/W: /opt/dapmeet/, /tmp/dapmeet-setup/   Read: /etc/dapmeet/   Execute deployment scripts	automation ALL=(ALL) NOPASSWD: /opt/dapmeet/scripts/deploy.sh automation ALL=(ALL) NOPASSWD: /usr/bin/systemctl restart dapmeet-* automation ALL=(dapmeet-backend) NOPASSWD: ALL automation ALL=(dapmeet-worker) NOPASSWD: ALL	/bin/bash	Yes (key only)	VM1, VM2	Client
monitoring	System monitoring	monitoring	-	  Read: /proc/, /sys/, /var/log/dapmeet/, /var/lib/postgresql/14/main/pg_stat/   Execute systemctl status	monitoring ALL=(ALL) NOPASSWD: /usr/bin/systemctl status * monitoring ALL=(ALL) NOPASSWD: /usr/bin/journalctl * monitoring ALL=(postgres) NOPASSWD: /usr/bin/psql -c "SELECT *"	/bin/bash	No (local only)	VM1, VM2	Server
backup	Backup automation	backup	postgres	  Read: /opt/dapmeet/, /etc/dapmeet/, /var/lib/postgresql/   R/W: /var/backups/dapmeet/   No interactive login	backup ALL=(postgres) NOPASSWD: /usr/bin/pg_dump backup ALL=(postgres) NOPASSWD: /usr/bin/pg_dumpall backup ALL=(ALL) NOPASSWD: /usr/bin/tar backup ALL=(ALL) NOPASSWD: /usr/bin/rsync	/bin/bash	No	VM2	Server
auditor	Security auditor (read-only)	auditor	-	  Read: /etc/dapmeet/, /var/log/dapmeet/, /opt/dapmeet/ (no .env)   Read: /var/lib/postgresql/ (metadata)   Strictly read-only	None	/bin/bash	Yes (key)	VM1, VM2	Client
deployer	Deployment specialist	deployer	dapmeet	  R/W: /opt/dapmeet/frontend/, /opt/dapmeet/backend/   Read: /etc/dapmeet/   Execute build/deploy scripts	deployer ALL=(ALL) NOPASSWD: /usr/bin/systemctl reload nginx deployer ALL=(dapmeet-backend) NOPASSWD: /opt/dapmeet/scripts/migrate.sh deployer ALL=(ALL) NOPASSWD: /usr/bin/npm * deployer ALL=(ALL) NOPASSWD: /usr/bin/python3 -m alembic *	/bin/bash	Yes (key)	VM1	Client

2. Create all groups and at least one user for each role.
Two VMs with separate scripts:
●	VM1 (Frontend): 8 groups, 7 users (nginx, deployer, sysadmin, devops_user, automation, monitoring, auditor)
●	VM2 (Backend/DB): 9 groups, 10 users (postgres, dapmeet-backend, dapmeet-worker, backup, sysadmin, devops_user, dba_user, automation, monitoring, auditor)
Scripts use groupadd, useradd, and usermod commands to create groups, system users,and assign memberships.  

3. Get a permissions for all groups
	Description
Two scripts configure filesystem permissions and sudoers rules for each VM.
VM1 (Frontend): Creates directories (/opt/dapmeet/frontend, /var/log/dapmeet, /etc/dapmeet/nginx), sets ownership (deployer:dapmeet, nginx:www-data), and configures sudoers for devops (nginx service management), deployer (nginx reload, npm), and monitoring (status/logs).
VM2 (Backend/DB): Creates directories (/opt/dapmeet/backend, /var/dapmeet/processing, /var/backups/dapmeet/postgresql), sets ownership (dapmeet-backend:dapmeet, backup:postgres), protects .env with 600, and configures sudoers for devops (dapmeet services), dba (PostgreSQL commands), automation (deployments), backup (pg_dump/rsync), and monitoring (status/logs).
All sudoers files placed in /etc/sudoers.d/ with 440 permissions.


  
4. Setting up an SSH connection
SSH key-based authentication was configured for the automation user to enable secure, passwordless access to both VMs.
Process:
Generated RSA 4096-bit key pair on client machine using ssh-keygen -t rsa -b 4096 -C "automation@dapmeet" -f ~/.ssh/automation_key
Created .ssh directory with 700 permissions and authorized_keys file with 600 permissions on both VMs
Verified setup with local SSH connections and file permission checks
The private key remains secure on the client machine while public keys enable authentication on target servers. This setup supports automated deployment processes once network routing is resolved.
  
 
