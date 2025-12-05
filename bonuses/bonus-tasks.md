# Bonus Tasks - Dapmeet Infrastructure

Based on the SIS implementations (SIS1-SIS6), these bonus tasks extend the automation and infrastructure capabilities.

---

## SIS Implementations Summary

| SIS | Topic | Implementation |
|-----|-------|----------------|
| SIS1 | Project Introduction | Dapmeet architecture: 2-VM setup (Frontend + Backend/DB) |
| SIS2 | Users & Permissions | Role tables, user scripts, SSH key authentication |
| SIS3 | Networking | Frontend setup, firewall configuration, smoke tests |
| SIS4 | Services | Docker containers, systemd services, cron jobs |
| SIS5 | Ansible Automation | Playbooks automating SIS 2, 3, 4 setup |
| SIS6 | Journaling & Auditing | journald, rsyslog, auditd configuration |

---

## Bonus Task 1: CI/CD Integration (4 points)

**Goal:** Integrate Ansible setup with GitHub Actions to automatically deploy infrastructure.

### Implementation: `bonus1-cicd/`

```
bonus1-cicd/
├── .github/
│   └── workflows/
│       ├── ansible-deploy.yml      # Main deployment pipeline
│       └── ansible-scheduled.yml   # Scheduled maintenance
├── .yamllint.yml                   # Linting configuration
├── verify-playbook.yml             # Post-deployment verification
└── README.md                       # Setup instructions
```

### Features

1. **Automated Deployment Pipeline**
   - Triggers on push to `main` branch
   - Lints YAML and Ansible syntax
   - Deploys to VMs via SSH
   - Runs verification tests

2. **Manual Trigger Options**
   - Select environment (staging/production)
   - Choose specific playbook
   - Filter by Ansible tags

3. **Scheduled Maintenance**
   - Weekly health checks
   - Security updates
   - Backup verification
   - Log rotation

### Quick Setup

```bash
# 1. Copy workflows to your repo
cp -r bonus1-cicd/.github /path/to/your/repo/

# 2. Add GitHub Secrets:
#    - ANSIBLE_SSH_PRIVATE_KEY
#    - VM1_HOST
#    - VM2_HOST  
#    - ANSIBLE_USER

# 3. Push to main branch - pipeline will run automatically
```

### Demo Steps

1. Push a change to `sis5/ansible/` directory
2. Go to GitHub Actions tab
3. Watch the pipeline execute
4. Verify deployment on VMs

---

## Bonus Task 2: Terraform Infrastructure (4 points)

**Goal:** Create Terraform configuration to provision VMs on Yandex Cloud.

### Implementation: `bonus2-terraform/`

```
bonus2-terraform/
├── main.tf                        # Main infrastructure definition
├── variables.tf                   # Variable definitions
├── outputs.tf                     # Output values
├── terraform.tfvars.example       # Example configuration
├── cloud-init/
│   ├── frontend.yaml              # VM1 initialization
│   └── backend.yaml               # VM2 initialization
├── .gitignore                     # Ignore sensitive files
└── README.md                      # Setup instructions
```

### Infrastructure Created

| Resource | Description |
|----------|-------------|
| VPC Network | Isolated network `dapmeet-network` |
| Subnet | `10.128.0.0/24` CIDR block |
| Security Group (Frontend) | Ports: 22, 80, 443, 3000 |
| Security Group (Backend) | Ports: 22, 8000, 5432 (internal) |
| VM1 (Frontend) | 2 cores, 2GB RAM, Ubuntu 22.04 |
| VM2 (Backend) | 2 cores, 4GB RAM, Ubuntu 22.04 |

### Quick Setup

```bash
cd bonus2-terraform

# 1. Configure Yandex Cloud CLI
yc init

# 2. Copy and edit variables
cp terraform.tfvars.example terraform.tfvars
vim terraform.tfvars

# 3. Initialize and apply
terraform init
terraform plan
terraform apply

# 4. Get Ansible inventory
terraform output -raw ansible_inventory > ../sis5/ansible/inventory/hosts.yml

# 5. Destroy when done
terraform destroy
```

### Demo Steps

1. Run `terraform plan` to show what will be created
2. Run `terraform apply` to create VMs
3. Show VMs in Yandex Cloud Console
4. SSH into VMs to verify
5. Run `terraform destroy` to clean up

---

## Integration Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        COMPLETE AUTOMATION FLOW                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌──────────────┐                                                       │
│  │  TERRAFORM   │ ──── Creates VMs on Yandex Cloud ────┐               │
│  │  (Bonus 2)   │                                       │               │
│  └──────────────┘                                       ▼               │
│                                                   ┌──────────┐          │
│                                                   │   VM1    │          │
│  ┌──────────────┐                                 │  VM2     │          │
│  │   GITHUB     │ ──── Triggers on push ────┐    └──────────┘          │
│  │   ACTIONS    │                            │         ▲               │
│  │  (Bonus 1)   │                            │         │               │
│  └──────────────┘                            │         │               │
│        │                                     │         │               │
│        ▼                                     │         │               │
│  ┌──────────────┐                            │         │               │
│  │   ANSIBLE    │ ◄──────────────────────────┘         │               │
│  │   (SIS5)     │ ──── Configures ─────────────────────┘               │
│  └──────────────┘                                                       │
│        │                                                                │
│        │ Sets up:                                                       │
│        ├── Users & Permissions (SIS2)                                   │
│        ├── Firewall (SIS3)                                              │
│        ├── Docker & Services (SIS4)                                     │
│        └── Journaling & Auditing (SIS6)                                 │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Grading Criteria

### Bonus Task 1 (4 points)
- [ ] GitHub Actions workflow exists and is properly configured
- [ ] Pipeline triggers on code changes
- [ ] Ansible playbook executes successfully on VMs
- [ ] Student can demonstrate the pipeline running

### Bonus Task 2 (4 points)
- [ ] Terraform configuration is valid (`terraform validate`)
- [ ] VMs are created on cloud platform
- [ ] Student can run `terraform apply` and show VMs created
- [ ] Student can run `terraform destroy` to clean up

---

## Files Structure

```
bonuses/
├── bonus-tasks.md              # This file
├── bonus1-cicd/                # CI/CD Integration
│   ├── .github/workflows/
│   │   ├── ansible-deploy.yml
│   │   └── ansible-scheduled.yml
│   ├── .yamllint.yml
│   ├── verify-playbook.yml
│   └── README.md
└── bonus2-terraform/           # Terraform IaC
    ├── main.tf
    ├── variables.tf
    ├── outputs.tf
    ├── terraform.tfvars.example
    ├── cloud-init/
    │   ├── frontend.yaml
    │   └── backend.yaml
    ├── .gitignore
    └── README.md
```
