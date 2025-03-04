-- AlterTable
ALTER TABLE "Job" ADD COLUMN     "experience" TEXT,
ADD COLUMN     "job_salary" TEXT,
ALTER COLUMN "job_type" DROP NOT NULL;
