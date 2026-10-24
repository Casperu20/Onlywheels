import { ChevronLeft, ChevronRight } from "lucide-react";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";

interface PaginationProps {
  page: number;
  pageSize: number;
  count: number;
  onChange: (page: number) => void;
}

export function Pagination({ page, pageSize, count, onChange }: PaginationProps) {
  const { t } = useTranslation();
  const pages = Math.max(1, Math.ceil(count / pageSize));
  if (pages <= 1) return null;

  return (
    <nav aria-label={t("catalog.pagination")} className="flex items-center justify-center gap-3">
      <Button variant="secondary" size="sm" disabled={page <= 1} onClick={() => onChange(page - 1)}>
        <ChevronLeft aria-hidden /> {t("catalog.previous")}
      </Button>
      <span className="text-sm text-muted-foreground">{t("catalog.pageOf", { page, pages })}</span>
      <Button variant="secondary" size="sm" disabled={page >= pages} onClick={() => onChange(page + 1)}>
        {t("catalog.next")} <ChevronRight aria-hidden />
      </Button>
    </nav>
  );
}
