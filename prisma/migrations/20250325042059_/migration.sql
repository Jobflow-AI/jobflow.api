/*
  Warnings:

  - The `content` column on the `ResumeSection` table would be dropped and recreated. This will lead to data loss if there is data in the column.

*/
-- AlterTable
ALTER TABLE "ResumeSection" DROP COLUMN "content",
ADD COLUMN     "content" JSONB[];

-- DropEnum
DROP TYPE "JobStatus";
