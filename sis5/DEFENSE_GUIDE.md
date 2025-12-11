# SIS5 Defense Guide: Automating All Setup + Bonus Tasks

**Student:** Abdurakhimov Abdussalam  
**Program:** Information Systems  
**Assignment:** SIS5 - Automating All Setup

---

## Table of Contents

1. [Overview](#overview)
2. [SIS5 Core Defense](#sis5-core-defense)
3. [Bonus Task 1: CI/CD Defense](#bonus-task-1-cicd-defense)
4. [Bonus Task 2: Terraform Defense](#bonus-task-2-terraform-defense)
5. [Complete Automation Flow Demo](#complete-automation-flow-demo)
6. [Expected Questions & Answers](#expected-questions--answers)
7. [Pre-Defense Checklist](#pre-defense-checklist)

---

## Overview

### What You Need to Show

1. **Deep Understanding** of Ansible automation
2. **Working Playbooks** that automate SIS 2, 3, and 4
3. **Bonus Tasks Integration** (CI/CD + Terraform)
4. **Practical Demonstration** of the complete automation flow

### Defense Structure

```
┌─────────────────────────────────────────────────────────────┐
│                     SIS5 DEFENSE (15-20 min)                 │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. Introduction (2 min)                                    │
│     - Project overview, architecture                        │
│                                                             │
│  2. SIS5 Core (8-10 min)                                    │
│     - Ansible playbook structure                            │
│     - Roles demonstration (SIS2, SIS3, SIS4)                │
│     - Live execution (or recorded demo)                     │
│                                                             │
│  3. Bonus Tasks (5-7 min)                                   │
│     - Bonus 1: CI/CD pipeline                               │
│     - Bonus 2: Terraform IaC                                │
│                                                             │
│  4. Integration Demo (3-5 min)                              │
│     - Complete flow: Terraform → Ansible → CI/CD            │
│                                                             │
│  5. Q&A (5 min)                                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## SIS5 Core Defense

### 1. Introduction Slide/Statement

**What to Say:**
> "SIS5 automates the complete infrastructure setup described in SIS2, SIS3, and SIS4 using Ansible. I've created a playbook that sets up users, permissions, SSH, firewall, Docker containers, systemd services, and cron jobs across two VMs (frontend and backend)."

### 2. Show Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Dapmeet Infrastructure                    │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  VM1 (Frontend)                    VM2 (Backend)            │
│  ──────────────                    ──────────────           │
│  • Next.js                         • FastAPI                │
│  • Nginx                           • PostgreSQL             │
│  • Docker Container                • Docker Container       │
│  • Systemd Service                 • Systemd Service        │
│  • Cron Jobs                       • Cron Jobs              │
│                                                             │
│  Ansible Playbook automates all of the above                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3. Demonstrate Playbook Structure

**Action:** Open terminal and show directory structure

```bash
cd sis5/ansible
tree -L 2
```

**Key Points to Explain:**
- **Inventory:** Defines VM1 and VM2 targets
- **Playbooks:** `site.yml` (both VMs), `vm1.yml`, `vm2.yml` (selective)
- **Roles:** Modular organization by functionality
- **Variables:** Group-specific and global variables

**What to Say:**
> "I've organized the playbook using Ansible best practices with roles for each component. This makes it modular, reusable, and easy to maintain."

### 4. Show Roles Implementation

**Demonstrate each role category:**

#### SIS2 Roles: Users & Permissions

```bash
# Show users role
cat roles/users/tasks/main.yml | head -30

# Show permissions role
cat roles/permissions/tasks/main.yml | head -30

# Show SSH role
cat roles/ssh/tasks/main.yml | head -30
```

**Key Points:**
- 12 users created across both VMs
- Proper group membership
- Directory structure with correct ownership
- SSH key-based authentication
- Sudoers configuration

#### SIS3 Roles: Networking

```bash
cat roles/firewall/tasks/main.yml
```

**Key Points:**
- UFW firewall configuration
- Ports: 22 (SSH), 80 (HTTP), 443 (HTTPS), 8000 (API), 5432 (PostgreSQL)
- Idempotent rules

#### SIS4 Roles: Services

```bash
# Show Docker role
cat roles/docker/tasks/main.yml | head -40

# Show services role
cat roles/services/tasks/main.yml

# Show cron role
cat roles/cron/tasks/main.yml
```

**Key Points:**
- Docker installation and configuration
- Pulling images from Docker Hub
- Systemd service units with auto-restart
- 4 cron jobs for backups and maintenance

### 5. Execute Playbook (Live or Pre-recorded)

**Option A: Live Execution (if VMs available)**

```bash
# Check connectivity
ansible all -i inventory/hosts.yml -m ping

# Show what would change (dry run)
ansible-playbook -i inventory/hosts.yml playbooks/site.yml --check

# Execute full playbook
ansible-playbook -i inventory/hosts.yml playbooks/site.yml -v
```

**Option B: Show Pre-recorded Demo**

- Recorded video of playbook execution
- Highlight key steps as they execute
- Show verification commands

### 6. Verification Steps

**After execution, verify:**

```bash
# Verify users
ansible all -i inventory/hosts.yml -m shell -a "getent passwd | grep dapmeet"

# Verify Docker
ansible all -i inventory/hosts.yml -m shell -a "docker ps"

# Verify services
ansible all -i inventory/hosts.yml -m shell -a "systemctl status dapmeet-* --no-pager"

# Verify firewall
ansible all -i inventory/hosts.yml -m shell -a "sudo ufw status numbered"

# Verify cron jobs
ansible all -i inventory/hosts.yml -m shell -a "sudo crontab -l -u automation"
```

### 7. Explain Key Ansible Concepts

**Demonstrate Understanding:**

1. **Idempotency**
   > "Ansible is idempotent, meaning I can run the playbook multiple times safely. It only makes changes when necessary."

2. **Idempotency Demo:**
   ```bash
   # Run twice - second time should show "changed=0"
   ansible-playbook -i inventory/hosts.yml playbooks/site.yml
   ansible-playbook -i inventory/hosts.yml playbooks/site.yml
   ```

3. **Tags for Selective Execution**
   ```bash
   # Only run SIS2 tasks
   ansible-playbook -i inventory/hosts.yml playbooks/site.yml --tags sis2
   
   # Only update Docker
   ansible-playbook -i inventory/hosts.yml playbooks/site.yml --tags docker
   ```

4. **Variables and Templates**
   > "I use Jinja2 templates for dynamic configuration. For example, systemd service files and cron scripts are templated based on variables."

---

## Bonus Task 1: CI/CD Defense

### Overview

**What to Say:**
> "Bonus Task 1 integrates the Ansible playbooks with GitHub Actions for automated deployment. Every time I push changes to the repository, it automatically deploys to the VMs."

### 1. Show Workflow Files

```bash
cd bonuses/bonus1-cicd
cat .github/workflows/ansible-deploy.yml | head -100
```

**Key Features to Highlight:**

1. **Automatic Triggers**
   - On push to `main` branch
   - On manual workflow dispatch
   - Path filters (only when `sis5/ansible/**` changes)

2. **Pipeline Stages**
   ```
   Lint → Syntax Check → Deploy → Verify → Notify
   ```

3. **Security**
   - Uses GitHub Secrets for SSH keys
   - Environment-specific deployments
   - Manual approval for production

### 2. Demonstrate GitHub Actions

**Action:** Open GitHub repository in browser

**Steps:**
1. Go to Actions tab
2. Show workflow runs
3. Click on a successful run
4. Show execution logs

**What to Say:**
> "The pipeline first lints the YAML files, then checks Ansible syntax, and finally deploys. All logs are stored as artifacts for debugging."

### 3. Show Scheduled Maintenance

```bash
cat .github/workflows/ansible-scheduled.yml
```

**Key Points:**
- Weekly automated maintenance
- Security updates
- Backup verification
- Log rotation

### 4. Integration Benefits

**What to Say:**
> "This CI/CD integration provides several benefits:
> - **Automation:** No manual SSH needed
> - **Consistency:** Same deployment process every time
> - **Audit Trail:** All deployments logged in GitHub
> - **Rollback:** Easy to revert with Git"

---

## Bonus Task 2: Terraform Defense

### Overview

**What to Say:**
> "Bonus Task 2 creates the VM infrastructure on Yandex Cloud using Terraform. This completes the Infrastructure as Code approach - we provision VMs with Terraform, then configure them with Ansible."

### 1. Show Terraform Configuration

```bash
cd bonuses/bonus2-terraform
ls -la
```

**Key Files:**
- `main.tf` - Infrastructure definition
- `variables.tf` - Configuration variables
- `outputs.tf` - Output values (IPs, inventory)
- `cloud-init/` - Initial VM configuration

### 2. Explain Infrastructure Created

**What to Say:**
> "Terraform creates:
> - VPC network with subnet
> - Security groups for frontend and backend
> - Two VMs (VM1: frontend, VM2: backend)
> - Cloud-init scripts for initial setup"

### 3. Demonstrate Terraform Commands

**Option A: Live Demo (if Yandex Cloud configured)**

```bash
# Initialize
terraform init

# Show what will be created
terraform plan

# Create infrastructure
terraform apply

# Show outputs
terraform output
```

**Option B: Explain with Screenshots**

Show:
- `terraform plan` output (what will be created)
- Yandex Cloud Console (created resources)
- `terraform output` showing VM IPs

### 4. Show Integration with Ansible

**What to Say:**
> "After Terraform creates the VMs, I generate the Ansible inventory automatically:"

```bash
# Generate Ansible inventory from Terraform outputs
terraform output -raw ansible_inventory > ../sis5/ansible/inventory/hosts.yml

# Now I can run Ansible immediately
cd ../sis5/ansible
ansible-playbook -i inventory/hosts.yml playbooks/site.yml
```

### 5. Cost Optimization

**What to Say:**
> "I've configured preemptible instances and optimized VM sizes. Estimated cost is $15-25/month for the complete infrastructure."

---

## Complete Automation Flow Demo

### The Full Circle

**What to Say:**
> "Here's the complete automation flow from scratch to production:"

```
┌─────────────────────────────────────────────────────────────┐
│              COMPLETE AUTOMATION FLOW                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. TERRAFORM (Bonus 2)                                     │
│     └─> Creates VMs on Yandex Cloud                        │
│         └─> Outputs: VM IPs, inventory                     │
│                                                             │
│  2. ANSIBLE (SIS5 Core)                                     │
│     └─> Configures VMs                                      │
│         ├─> SIS2: Users, permissions, SSH                  │
│         ├─> SIS3: Firewall                                 │
│         └─> SIS4: Docker, services, cron                   │
│                                                             │
│  3. CI/CD (Bonus 1)                                         │
│     └─> Automates future deployments                        │
│         └─> Triggered on code changes                      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Live Demo Flow

**Step 1: Provision Infrastructure**
```bash
cd bonuses/bonus2-terraform
terraform apply -auto-approve
terraform output ansible_inventory > ../sis5/ansible/inventory/hosts.yml
```

**Step 2: Configure with Ansible**
```bash
cd ../sis5/ansible
ansible-playbook -i inventory/hosts.yml playbooks/site.yml
```

**Step 3: Verify Setup**
```bash
ansible all -i inventory/hosts.yml -m shell -a "docker ps"
ansible all -i inventory/hosts.yml -m shell -a "systemctl status dapmeet-*"
```

**Step 4: Show CI/CD**
- Push a change to `sis5/ansible/`
- Show GitHub Actions running
- Show deployment logs

### Benefits Summary

**What to Say:**
> "This complete automation provides:
> 1. **Infrastructure as Code:** Everything in version control
> 2. **Reproducibility:** Identical environments every time
> 3. **Scalability:** Easy to add more VMs
> 4. **Maintainability:** Changes tracked in Git
> 5. **Automation:** Minimal manual intervention"

---

## Expected Questions & Answers

### General Ansible Questions

**Q: What is idempotency and why is it important?**

**A:**
> "Idempotency means running the same playbook multiple times produces the same result. It's important because:
> - Safe to rerun without breaking things
> - Only makes necessary changes
> - Handles partial failures gracefully
> 
> For example, if Docker is already installed, the task will report 'ok' instead of trying to reinstall it."

**Q: How do you handle secrets in Ansible?**

**A:**
> "I use Ansible Vault for sensitive data like passwords. In production, I also use:
> - Environment variables
> - GitHub Secrets (for CI/CD)
> - SSH key-based authentication instead of passwords
> 
> Currently, the playbook uses SSH keys and avoids storing secrets in plain text."

**Q: What happens if a task fails in the middle of execution?**

**A:**
> "Ansible stops execution by default on errors. However, I've configured:
> - Proper error handling with `ignore_errors` where appropriate
> - Handlers for restarting services after changes
> - Check mode (`--check`) to preview changes
> 
> The playbook can be rerun and will continue from where it left off."

### SIS-Specific Questions

**Q: How does your playbook handle SIS2, SIS3, and SIS4 requirements?**

**A:**
> "I've organized it into roles:
> - **SIS2:** `users`, `permissions`, `ssh` roles create all required users, set permissions, and configure SSH
> - **SIS3:** `firewall` role configures UFW with all required ports
> - **SIS4:** `docker`, `services`, `cron` roles install Docker, create systemd services, and schedule cron jobs
> 
> Each role is tagged, so I can run specific parts independently."

**Q: How do you verify that everything was set up correctly?**

**A:**
> "I use several verification methods:
> 1. Ansible return values check task success
> 2. Ad-hoc commands verify configuration: `ansible all -m shell -a "docker ps"`
> 3. Verification scripts check services and connectivity
> 4. CI/CD pipeline includes post-deployment verification
> 
> All verification steps are documented in the README."

### Bonus Task Questions

**Q: How does CI/CD integrate with your Ansible playbooks?**

**A:**
> "The GitHub Actions workflow:
> 1. Triggers automatically on pushes to `sis5/ansible/`
> 2. Lints and validates the playbooks
> 3. Executes the playbooks on target VMs via SSH
> 4. Runs verification tests
> 5. Stores logs as artifacts
> 
> This means any infrastructure change is automatically deployed, with full audit trail."

**Q: What's the advantage of using Terraform before Ansible?**

**A:**
> "Terraform is ideal for provisioning infrastructure (VMs, networks, security groups), while Ansible excels at configuration management (installing software, configuring services).
> 
> The workflow is:
> - Terraform: **Creates** the infrastructure
> - Ansible: **Configures** the infrastructure
> 
> This separation of concerns makes the process more modular and maintainable."

**Q: How would you handle multiple environments (dev, staging, production)?**

**A:**
> "I've designed the solution with environments in mind:
> 1. **Terraform:** Uses `environment` variable to tag resources and adjust sizes
> 2. **Ansible:** Uses `group_vars` for environment-specific variables
> 3. **CI/CD:** Supports environment selection via workflow inputs
> 
> I can deploy the same codebase to different environments by changing variables."

### Technical Deep-Dive Questions

**Q: How do you ensure security in your automation?**

**A:**
> "Security measures:
> 1. SSH key-based authentication (no passwords)
> 2. Firewall rules restrict access to required ports only
> 3. Users have minimal necessary privileges (sudoers rules)
> 4. Secrets stored in GitHub Secrets, not in code
> 5. Regular security updates via scheduled maintenance
> 6. Audit logs via SIS6 journaling (if applicable)"

**Q: How would you scale this to more VMs?**

**A:**
> "The playbook is already designed for scalability:
> 1. **Inventory:** Easy to add more hosts to `inventory/hosts.yml`
> 2. **Roles:** Reusable across any number of VMs
> 3. **Variables:** Group-based variables handle different VM types
> 4. **Terraform:** Can create multiple VMs with `count` or `for_each`
> 
> I can add a load balancer VM by:
> - Adding it to Terraform
> - Creating a new inventory group
> - Using existing roles with appropriate tags"

**Q: What happens if you need to rollback changes?**

**A:**
> "Rollback strategy:
> 1. **Git:** Revert commits and push (CI/CD will redeploy)
> 2. **Ansible:** Run previous version of playbook from Git history
> 3. **Terraform:** Can destroy and recreate, or use `terraform state` to rollback
> 4. **Services:** Systemd services can be rolled back by changing Docker image tags
> 
> Since everything is version-controlled, rollback is straightforward."

---

## Pre-Defense Checklist

### Technical Preparation

- [ ] **VMs Accessible**
  - [ ] SSH keys work
  - [ ] Can ping both VMs
  - [ ] Test playbook execution

- [ ] **GitHub Repository**
  - [ ] All code pushed and up-to-date
  - [ ] README files complete
  - [ ] Links work correctly

- [ ] **Demo Environment**
  - [ ] VMs can be reset/cleaned if needed
  - [ ] Backup of working configuration
  - [ ] Pre-recorded demo video as backup

- [ ] **Terraform (Bonus 2)**
  - [ ] Yandex Cloud credentials configured
  - [ ] Test `terraform plan` works
  - [ ] Screenshots of created resources

- [ ] **CI/CD (Bonus 1)**
  - [ ] GitHub Actions workflows pushed
  - [ ] Secrets configured
  - [ ] At least one successful run in history

### Documentation

- [ ] **Report**
  - [ ] Full name, group, program included
  - [ ] Topic, target, tasks described
  - [ ] Step-by-step implementation
  - [ ] Conclusions section
  - [ ] Repository link included
  - [ ] Format: 14pt Times New Roman, bold headers

- [ ] **README Files**
  - [ ] `sis5/ansible/README.md` complete
  - [ ] `bonuses/bonus1-cicd/README.md` complete
  - [ ] `bonuses/bonus2-terraform/README.md` complete

- [ ] **Code Comments**
  - [ ] Key roles and tasks commented
  - [ ] Complex logic explained

### Presentation Materials

- [ ] **Slides (optional)**
  - [ ] Architecture diagram
  - [ ] Automation flow diagram
  - [ ] Key metrics/statistics

- [ ] **Terminal Commands**
  - [ ] Prepare command snippets
  - [ ] Test all commands beforehand
  - [ ] Have backup plans for failed commands

- [ ] **Screenshots**
  - [ ] GitHub Actions runs
  - [ ] Terraform outputs
  - [ ] VM configurations
  - [ ] Service status

### Understanding Check

- [ ] **Can explain:**
  - [ ] Every role and its purpose
  - [ ] Why specific design choices were made
  - [ ] How idempotency works
  - [ ] Difference between Ansible and Terraform
  - [ ] CI/CD pipeline stages
  - [ ] How to troubleshoot common issues

### Practice Run

- [ ] **Rehearse:**
  - [ ] Full presentation (15-20 min)
  - [ ] Demo execution
  - [ ] Answering common questions
  - [ ] Handling technical difficulties

---

## Quick Reference Commands

### SIS5 Core

```bash
# Test connectivity
ansible all -i inventory/hosts.yml -m ping

# Dry run
ansible-playbook -i inventory/hosts.yml playbooks/site.yml --check

# Full deployment
ansible-playbook -i inventory/hosts.yml playbooks/site.yml -v

# Verify users
ansible all -i inventory/hosts.yml -m shell -a "getent passwd | grep dapmeet"

# Verify Docker
ansible all -i inventory/hosts.yml -m shell -a "docker ps"

# Verify services
ansible all -i inventory/hosts.yml -m shell -a "systemctl status dapmeet-* --no-pager"
```

### Bonus 1 (CI/CD)

```bash
# View workflow
cat .github/workflows/ansible-deploy.yml

# Trigger manually via GitHub UI: Actions → Deploy Dapmeet Infrastructure → Run workflow
```

### Bonus 2 (Terraform)

```bash
cd bonuses/bonus2-terraform

# Plan
terraform plan

# Apply
terraform apply

# Get outputs
terraform output

# Generate Ansible inventory
terraform output -raw ansible_inventory > ../sis5/ansible/inventory/hosts.yml

# Destroy
terraform destroy
```

---

## Final Tips

1. **Be Confident:** You've built a complete automation solution - own it!

2. **Show Understanding:** Don't just run commands - explain why you made each choice.

3. **Handle Failures Gracefully:** If something doesn't work during demo, explain how you'd troubleshoot it.

4. **Emphasize Integration:** Highlight how Terraform → Ansible → CI/CD work together.

5. **Time Management:** Practice your timing. Don't rush, but stay within time limits.

6. **Backup Plans:** Have screenshots/videos ready if live demo fails.

7. **Ask for Questions:** Engage with the evaluator - show you understand the deeper concepts.

---

**Good luck with your defense! 🚀**

