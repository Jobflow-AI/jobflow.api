/*
  Warnings:

  - You are about to drop the column `resumeData` on the `User` table. All the data in the column will be lost.

*/
-- AlterTable
ALTER TABLE "User" DROP COLUMN "resumeData";

-- AddForeignKey
ALTER TABLE "ResumeSection" ADD CONSTRAINT "ResumeSection_userId_fkey" FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE RESTRICT ON UPDATE CASCADE;
