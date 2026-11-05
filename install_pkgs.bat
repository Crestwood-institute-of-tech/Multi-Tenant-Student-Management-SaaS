@echo off
cd /d "C:\Users\ThinkPad\Desktop\proj\Multi-Tenant Student Management SaaS\frontend"
npm install lucide-react react-hook-form zod @tanstack/react-query clsx tailwind-merge class-variance-authority @radix-ui/react-slot > "C:\Users\ThinkPad\Desktop\proj\Multi-Tenant Student Management SaaS\install.log" 2>&1
echo EXIT=%ERRORLEVEL% >> "C:\Users\ThinkPad\Desktop\proj\Multi-Tenant Student Management SaaS\install.log"
