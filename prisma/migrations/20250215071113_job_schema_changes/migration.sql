/*
  Warnings:

  - A unique constraint covering the columns `[job_id]` on the table `Job` will be added. If there are existing duplicate values, this will fail.
  - A unique constraint covering the columns `[job_id]` on the table `Tracked_Jobs` will be added. If there are existing duplicate values, this will fail.

*/
-- AlterTable
ALTER TABLE "Job" ADD COLUMN     "job_id" TEXT;

-- AlterTable
ALTER TABLE "Tracked_Jobs" ADD COLUMN     "experience" TEXT,
ADD COLUMN     "experience_max" INTEGER,
ADD COLUMN     "experience_min" INTEGER,
ADD COLUMN     "job_id" TEXT,
ADD COLUMN     "salary_max" DOUBLE PRECISION,
ADD COLUMN     "salary_min" DOUBLE PRECISION;

-- CreateIndex
CREATE UNIQUE INDEX "Job_job_id_key" ON "Job"("job_id");

-- CreateIndex
CREATE UNIQUE INDEX "Tracked_Jobs_job_id_key" ON "Tracked_Jobs"("job_id");

-- RenameIndex
ALTER INDEX "Company_company_name_key" RENAME TO "UniqueCompanyName";

-- RenameIndex
ALTER INDEX "Job_title_companyId_key" RENAME TO "UniqueJobTitleCompany";

-- RenameIndex
ALTER INDEX "Tracked_Jobs_title_companyId_userId_key" RENAME TO "UniqueTrackedJob";
