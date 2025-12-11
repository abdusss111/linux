# SIS5 Defense Quick Checklist

Print this page or keep it open during your defense.

---

## ✅ Pre-Defense Setup

### Technical Readiness
- [ ] Both VMs are accessible via SSH
- [ ] Ansible can ping both VMs (`ansible all -m ping`)
- [ ] Playbooks tested and working
- [ ] GitHub repository is up-to-date
- [ ] GitHub Actions workflows configured (Bonus 1)
- [ ] Terraform configured/tested (Bonus 2)
- [ ] Backup demo video recorded (if needed)

### Documentation
- [ ] Report formatted correctly (14pt Times New Roman, bold headers)
- [ ] Full name, group, program included
- [ ] Repository link included
- [ ] All README files complete

### Presentation Materials
- [ ] Terminal window ready with commands
- [ ] GitHub repository open in browser
- [ ] Screenshots/videos ready as backup
- [ ] Architecture diagram prepared (if using slides)

---

## 🎯 Defense Flow (15-20 min)

### Opening (2 min)
- [ ] Introduce yourself (name, program)
- [ ] State SIS topic and target
- [ ] Mention bonus tasks completed
- [ ] Show architecture overview

### SIS5 Core (8-10 min)

#### Playbook Structure (2 min)
- [ ] Show directory structure (`tree -L 2`)
- [ ] Explain inventory, playbooks, roles, variables
- [ ] Emphasize modular organization

#### SIS2 Roles (2 min)
- [ ] Show users role - explain 12 users created
- [ ] Show permissions role - directory structure
- [ ] Show SSH role - key-based auth
- [ ] Mention idempotency

#### SIS3 Roles (1 min)
- [ ] Show firewall role
- [ ] Explain ports: 22, 80, 443, 8000, 5432
- [ ] Mention UFW configuration

#### SIS4 Roles (2 min)
- [ ] Show Docker role - installation and images
- [ ] Show services role - systemd units
- [ ] Show cron role - 4 scheduled tasks
- [ ] Show template example (systemd service)

#### Execution Demo (2-3 min)
- [ ] Execute playbook OR show pre-recorded demo
- [ ] Show verification commands
- [ ] Demonstrate idempotency (run twice)

#### Ansible Concepts (1 min)
- [ ] Explain idempotency
- [ ] Demonstrate tags (`--tags docker`)
- [ ] Show variable usage

### Bonus Tasks (5-7 min)

#### Bonus 1: CI/CD (3 min)
- [ ] Open GitHub Actions in browser
- [ ] Show workflow file structure
- [ ] Explain pipeline stages (Lint → Deploy → Verify)
- [ ] Mention scheduled maintenance
- [ ] Show successful run (if available)

#### Bonus 2: Terraform (2-3 min)
- [ ] Show Terraform directory structure
- [ ] Explain what it creates (VPC, VMs, security groups)
- [ ] Show integration with Ansible (inventory generation)
- [ ] Mention cost optimization

### Integration Demo (3-5 min)
- [ ] Show complete flow diagram
- [ ] Explain: Terraform → Ansible → CI/CD
- [ ] Execute or show recorded demo
- [ ] Emphasize benefits

### Conclusions (2 min)
- [ ] Summarize what was accomplished
- [ ] List key benefits (reproducibility, version control, etc.)
- [ ] Mention lessons learned
- [ ] Provide repository link

---

## 💬 Key Points to Remember

### Always Mention:
- ✅ **Idempotency** - safe to run multiple times
- ✅ **Modular design** - reusable roles
- ✅ **Infrastructure as Code** - everything in Git
- ✅ **Complete automation** - Terraform + Ansible + CI/CD
- ✅ **Version control** - all changes tracked

### Demonstrate Understanding:
- ✅ Why you chose Ansible roles structure
- ✅ How idempotency works in practice
- ✅ Difference between Terraform and Ansible
- ✅ How CI/CD integrates with playbooks
- ✅ Security considerations

---

## 🛠️ Command Quick Reference

### Must-Have Commands Ready:

```bash
# Connectivity test
ansible all -i inventory/hosts.yml -m ping

# Execute playbook
ansible-playbook -i inventory/hosts.yml playbooks/site.yml -v

# Show structure
tree -L 2

# Verify setup
ansible all -i inventory/hosts.yml -m shell -a "docker ps"
ansible all -i inventory/hosts.yml -m shell -a "systemctl status dapmeet-*"

# Show tags
ansible-playbook -i inventory/hosts.yml playbooks/site.yml --tags docker --check
```

---

## ❓ Common Questions - Quick Answers

### "What is idempotency?"
→ "Ansible checks current state first. Running the same playbook multiple times produces the same result. If Docker is already installed, it won't try to reinstall."

### "How do you handle errors?"
→ "Ansible stops on errors by default. Playbook can be rerun - it continues from where it left off. I use handlers for service restarts and check mode for preview."

### "Why separate Terraform and Ansible?"
→ "Terraform provisions infrastructure (creates VMs), Ansible configures them (installs software). Separation of concerns makes each tool do what it's best at."

### "How do you manage secrets?"
→ "SSH key-based auth, no passwords. GitHub Secrets for CI/CD. Ansible Vault can be used for sensitive variables. Secrets never stored in code."

### "How would you add more VMs?"
→ "Add hosts to inventory.yml, use existing roles. Terraform can create multiple VMs with count. Same playbook, just more targets."

---

## 🚨 Troubleshooting Backup Plan

### If Live Demo Fails:

1. **Playbook doesn't run?**
   → "Let me show you the pre-recorded demo instead" OR explain what would happen

2. **VM not accessible?**
   → "I'll show you the GitHub Actions logs from a previous successful run"

3. **Command doesn't work?**
   → Show the configuration files and explain what the command does

4. **Terraform not working?**
   → Show configuration files and explain the architecture, show screenshots

### Always Have:
- [ ] Pre-recorded video
- [ ] Screenshots of successful runs
- [ ] GitHub Actions logs
- [ ] Configuration files ready to show

---

## 📊 Success Indicators

You'll know you're doing well if:
- ✅ Evaluator is engaged and asking questions
- ✅ You can explain every component confidently
- ✅ Demo works smoothly (or you handle issues gracefully)
- ✅ You connect concepts (e.g., "This role implements SIS2 requirement X")
- ✅ You mention best practices and why you chose them

---

## 🎓 Final Tips

1. **Breathe** - Take your time, don't rush
2. **Pause** - After explaining a concept, pause to check understanding
3. **Engage** - Ask if they want to see more detail on any part
4. **Be Honest** - If you don't know something, say so but explain how you'd find out
5. **Show Enthusiasm** - You built something cool, be proud of it!

---

## 📝 Post-Defense Notes

After defense, write down:
- Questions you were asked
- What went well
- What you'd improve
- Feedback received

---

**You've got this! Good luck! 🚀**

---

*Print this checklist and keep it nearby during your defense.*

