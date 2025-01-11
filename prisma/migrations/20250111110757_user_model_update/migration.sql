/*
  Warnings:

  - The `job_statuses` column on the `User` table would be dropped and recreated. This will lead to data loss if there is data in the column.

*/
-- AlterTable
ALTER TABLE "User" DROP COLUMN "job_statuses",
ADD COLUMN     "job_statuses" JSONB NOT NULL DEFAULT '[{"bookmarked": {"total": 0}, "applied": {"total": 0}, "accepted": {"total": 0}, "rejected": {"total": 0}}]';
