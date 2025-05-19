-- DropForeignKey
ALTER TABLE "ResumeSection" DROP CONSTRAINT "ResumeSection_userId_fkey";

-- AlterTable
ALTER TABLE "User" ADD COLUMN     "resumeData" JSONB;
