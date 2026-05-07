import { useState } from 'react';

interface PaginationState {
  page: number;
  pageSize: number;
}

export function usePagination(defaultPageSize = 20) {
  const [pagination, setPagination] = useState<PaginationState>({
    page: 1,
    pageSize: defaultPageSize,
  });

  const onChange = (page: number, pageSize: number) => {
    setPagination({ page, pageSize });
  };

  return {
    page: pagination.page,
    pageSize: pagination.pageSize,
    onChange,
    reset: () => setPagination({ page: 1, pageSize: defaultPageSize }),
  };
}
