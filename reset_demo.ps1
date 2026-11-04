# Recreates the much_demo database from scratch with the project_sprint demo data.
# Run from the Much folder:  .\reset_demo.ps1
docker compose exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS much_demo WITH (FORCE);"
docker compose exec -T odoo rm -rf /var/lib/odoo/filestore/much_demo
docker compose exec -T odoo odoo -d much_demo --db_host db --db_user odoo --db_password odoo -i project_sprint --stop-after-init --http-port 8070 --log-level=warn
Write-Host "much_demo recreated. Log in at http://localhost:8069/web/database/selector (admin / admin)."
