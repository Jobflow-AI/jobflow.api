/*
  Warnings:

  - You are about to drop the column `job_salary` on the `Job` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "Job" DROP COLUMN "job_salary",
ADD COLUMN     "experience_max" INTEGER,
ADD COLUMN     "experience_min" INTEGER,
ADD COLUMN     "salary_max" DOUBLE PRECISION,
ADD COLUMN     "salary_min" DOUBLE PRECISION;
