# SIS5 Defense Presentation Script

**Estimated Time: 15-20 minutes**

---

## Opening (2 minutes)

### Introduction
> "Good [morning/afternoon]. My name is Abdurakhimov Abdussalam, Information Systems program.
> 
> Today I'll present SIS5: Automating All Setup, where I've created Ansible playbooks to automate the complete infrastructure setup from SIS2, SIS3, and SIS4.
> 
> I've also completed two bonus tasks:
> - Bonus Task 1: CI/CD Integration with GitHub Actions
> - Bonus Task 2: Terraform Infrastructure as Code
> 
> Let me start with an overview of the project architecture."

---

## Part 1: Project Overview (1 minute)

### Architecture
> "Dapmeet is a service for transcribing Google Meet meetings and generating summaries using AI.
> 
> The infrastructure consists of two VMs:
> - **VM1 (Frontend):** Next.js application, Nginx, Docker container
> - **VM2 (Backend):** FastAPI backend, PostgreSQL database, Docker container
> 
> Previously, setup was done manually with shell scripts. Now, I've automated everything with Ansible."

---

## Part 2: SIS5 Core - Ansible Playbooks (8-10 minutes)

### 2.1 Playbook Structure (2 min)

**Action:** Open terminal, show directory structure

```bash
cd sis5/ansible
tree -L 2
```

> "I've organized the playbook using Ansible best practices:
> 
> - **Inventory:** Defines VM1 and VM2 as targets
> - **Playbooks:** `site.yml` for both VMs, `vm1.yml` and `vm2.yml` for selective deployment
> - **Roles:** Modular organization - one role per functionality
> - **Variables:** Group-specific variables in `group_vars/`
> 
> This modular structure makes the playbook maintainable and reusable."

### 2.2 SIS2 Implementation: Users & Permissions (2 min)

**Action:** Show roles/users/tasks/main.yml

> "For SIS2, I created three roles:
> 
> 1. **Users role:** Creates 12 users across both VMs including postgres, nginx, dapmeet-backend, sysadmin, and devops_user. Each user has proper group membership.
> 
> 2. **Permissions role:** Sets up directory structure with correct ownership, and configures sudoers rules.
> 
> 3. **SSH role:** Configures SSH with key-based authentication and disables root login for security."

**Show example:**
```bash
cat roles/users/tasks/main.yml | head -20
```

### 2.3 SIS3 Implementation: Networking (1 min)

**Action:** Show roles/firewall/tasks/main.yml

> "For SIS3, I created the firewall role that configures UFW with the required ports:
> - Port 22 for SSH
> - Port 80 for HTTP
> - Port 443 for HTTPS  
> - Port 8000 for the API
> - Port 5432 for PostgreSQL (internal only)
> 
> The configuration is idempotent, meaning it's safe to run multiple times."

### 2.4 SIS4 Implementation: Services (2 min)

**Action:** Show Docker, services, and cron roles

> "For SIS4, I created three roles:
> 
> 1. **Docker role:** Installs Docker, adds users to docker group, and pulls images from Docker Hub.
> 
> 2. **Services role:** Creates systemd unit files for containers with auto-restart capability.
> 
> 3. **Cron role:** Sets up 4 scheduled tasks - log backups, database backups, SSL renewal checks, and log rotation."

**Show systemd template:**
```bash
cat roles/services/templates/docker-container.service.j2
```

### 2.5 Live Execution Demo (2-3 min)

**Option A: Live Execution**
```bash
# Show connectivity
ansible all -i inventory/hosts.yml -m ping

# Execute playbook (or show pre-run state)
ansible-playbook -i inventory/hosts.yml playbooks/site.yml
```

**Option B: Show Pre-recorded Demo**
> "Let me show you a recorded execution. As you can see, Ansible creates all users, configures permissions, sets up firewall, installs Docker, and starts services. The execution is idempotent - running it again would show minimal changes."

### 2.6 Key Ansible Concepts (1 min)

> "I want to highlight two important concepts:
> 
> 1. **Idempotency:** Ansible checks the current state and only makes changes when necessary. This means I can run the playbook multiple times safely.
> 
> 2. **Tags:** I can run specific parts using tags. For example, `--tags sis2` runs only SIS2 tasks, or `--tags docker` runs only Docker setup."

**Demonstrate:**
```bash
# Show tags
ansible-playbook -i inventory/hosts.yml playbooks/site.yml --tags docker --check
```

---

## Part 3: Bonus Tasks (5-7 minutes)

### 3.1 Bonus Task 1: CI/CD Integration (3 min)

**Action:** Open GitHub repository → Actions tab

> "Bonus Task 1 integrates Ansible with GitHub Actions for automated deployment.
> 
> The workflow triggers automatically when I push changes to the `sis5/ansible/` directory. Here's the pipeline flow:
> 
> 1. **Lint:** Validates YAML and Ansible syntax
> 2. **Syntax Check:** Verifies playbook syntax
> 3. **Deploy:** Executes the playbook on target VMs
> 4. **Verify:** Runs post-deployment checks
> 
> This means any infrastructure change is automatically deployed with full audit trail in GitHub."

**Show workflow file:**
```bash
cat bonuses/bonus1-cicd/.github/workflows/ansible-deploy.yml | head -60
```

> "I also created a scheduled workflow that runs weekly maintenance tasks like security updates and backup verification."

### 3.2 Bonus Task 2: Terraform Infrastructure (2-3 min)

**Action:** Open Terraform directory or show Yandex Cloud console

> "Bonus Task 2 creates the VM infrastructure on Yandex Cloud using Terraform.
> 
> This completes the Infrastructure as Code approach:
> - **Terraform:** Creates infrastructure (VMs, networks, security groups)
> - **Ansible:** Configures infrastructure (software, services, users)
> 
> Let me show you what Terraform creates:"

**Show main.tf structure:**
```bash
cd bonuses/bonus2-terraform
cat main.tf | head -50
```

> "Terraform creates:
> - VPC network and subnet
> - Security groups with proper firewall rules
> - Two VMs (VM1: 2 cores, 2GB RAM; VM2: 2 cores, 4GB RAM)
> - Cloud-init scripts for initial VM setup
> 
> After Terraform creates the VMs, I can automatically generate the Ansible inventory:"

```bash
terraform output -raw ansible_inventory > ../sis5/ansible/inventory/hosts.yml
```

> "This connects Terraform and Ansible seamlessly."

---

## Part 4: Complete Integration Demo (3-5 minutes)

### The Full Automation Flow

> "Now let me show you the complete automation flow from scratch to production:"

```
1. TERRAFORM creates VMs on Yandex Cloud
   └─> Outputs: VM IPs and Ansible inventory

2. ANSIBLE configures the VMs
   ├─> SIS2: Users, permissions, SSH
   ├─> SIS3: Firewall
   └─> SIS4: Docker, services, cron

3. CI/CD automates future deployments
   └─> Triggered on every code change
```

**Live Demo Flow (if possible):**

```bash
# Step 1: Provision infrastructure
cd bonuses/bonus2-terraform
terraform apply -auto-approve
terraform output ansible_inventory > ../sis5/ansible/inventory/hosts.yml

# Step 2: Configure with Ansible
cd ../sis5/ansible
ansible-playbook -i inventory/hosts.yml playbooks/site.yml

# Step 3: Verify
ansible all -i inventory/hosts.yml -m shell -a "docker ps"
```

> "The complete flow from zero to production-ready infrastructure takes about 10-15 minutes, and it's fully automated and reproducible."

---

## Part 5: Benefits & Conclusions (2 minutes)

### Benefits

> "This automation solution provides several key benefits:
> 
> 1. **Reproducibility:** Identical environments every time, anywhere
> 2. **Version Control:** All infrastructure changes tracked in Git
> 3. **Scalability:** Easy to add more VMs or environments
> 4. **Maintainability:** Modular roles make updates easy
> 5. **Automation:** Minimal manual intervention required
> 6. **Documentation:** Code itself documents the infrastructure"

### Lessons Learned

> "Key takeaways from this project:
> - Infrastructure as Code is essential for modern DevOps
> - Separation of concerns (Terraform vs Ansible) improves maintainability
> - CI/CD integration enables continuous deployment
> - Proper organization (roles, variables) makes playbooks manageable"

### Future Improvements

> "Potential improvements:
> - Add monitoring and alerting
> - Implement blue-green deployments
> - Add automated testing
> - Expand to multiple environments (dev, staging, prod)
> - Implement secrets management with Vault"

---

## Closing (1 minute)

> "To summarize:
> 
> I've successfully automated the complete infrastructure setup from SIS2, SIS3, and SIS4 using Ansible playbooks organized into reusable roles.
> 
> I've integrated CI/CD with GitHub Actions for automated deployments and used Terraform for infrastructure provisioning, completing the full Infrastructure as Code solution.
> 
> All code is available in the GitHub repository: [provide link]
> 
> Thank you for your attention. I'm ready for questions."

---

## Transition to Q&A

> "I'm happy to answer any questions or demonstrate specific aspects in more detail."

---

## Tips During Presentation

1. **Pace Yourself:** Don't rush. Speak clearly and pause between sections.

2. **Engage:** Make eye contact, check if the evaluator understands.

3. **Be Flexible:** If interrupted, answer the question, then continue.

4. **Show Confidence:** You know this material - present it with authority.

5. **Use Examples:** When explaining concepts, give concrete examples.

6. **Handle Mistakes:** If something doesn't work, explain how you'd troubleshoot it.

7. **Time Awareness:** Keep track of time. You have ~15-20 minutes total.

---

## Quick Command Reference (Have Open)

```bash
# Connectivity
ansible all -i inventory/hosts.yml -m ping

# Execute
ansible-playbook -i inventory/hosts.yml playbooks/site.yml -v

# Verify
ansible all -i inventory/hosts.yml -m shell -a "docker ps"
ansible all -i inventory/hosts.yml -m shell -a "systemctl status dapmeet-*"

# Terraform
terraform plan
terraform apply
terraform output

# Tags
ansible-playbook -i inventory/hosts.yml playbooks/site.yml --tags docker
```

---

**Good luck! 🚀**

