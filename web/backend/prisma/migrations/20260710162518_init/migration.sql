-- AlterEnum
ALTER TYPE "DocumentStatus" ADD VALUE 'SUPERSEDED';

-- AlterTable
ALTER TABLE "documents" ADD COLUMN     "is_latest" BOOLEAN NOT NULL DEFAULT true,
ADD COLUMN     "parent_document_id" UUID,
ADD COLUMN     "superseded_at" TIMESTAMP(3),
ADD COLUMN     "version" INTEGER NOT NULL DEFAULT 1;

-- CreateIndex
CREATE INDEX "documents_original_name_department_id_is_latest_idx" ON "documents"("original_name", "department_id", "is_latest");

-- AddForeignKey
ALTER TABLE "documents" ADD CONSTRAINT "documents_parent_document_id_fkey" FOREIGN KEY ("parent_document_id") REFERENCES "documents"("id") ON DELETE SET NULL ON UPDATE CASCADE;
