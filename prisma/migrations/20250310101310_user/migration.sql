-- AlterTable
ALTER TABLE "User" ADD COLUMN     "resume" JSONB,
ADD COLUMN     "resume_education" JSONB,
ADD COLUMN     "resume_experience" JSONB,
ADD COLUMN     "resume_links" JSONB,
ADD COLUMN     "resume_location" TEXT,
ADD COLUMN     "resume_phone" TEXT,
ADD COLUMN     "resume_projects" JSONB,
ADD COLUMN     "resume_skills" TEXT[],
ADD COLUMN     "resume_summary" TEXT;
