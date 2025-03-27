-- AlterTable
ALTER TABLE "Company" ADD COLUMN     "source" TEXT[];

-- CreateIndex
CREATE INDEX "Job_title_idx" ON "Job"("title");

-- CreateIndex
CREATE INDEX "Job_job_location_idx" ON "Job"("job_location");

-- CreateIndex
CREATE INDEX "Job_salary_min_idx" ON "Job"("salary_min");

-- CreateIndex
CREATE INDEX "Job_salary_max_idx" ON "Job"("salary_max");

-- CreateIndex
CREATE INDEX "Job_status_idx" ON "Job"("status");
