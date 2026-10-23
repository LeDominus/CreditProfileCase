'use client'

import { useProducts } from '@/fsd/entities/product/model/queries'
import { formatMoney, formatRate } from '@/fsd/shared/lib/format'
import { Button } from '@/fsd/shared/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/fsd/shared/ui/dialog'
import { Skeleton } from '@/fsd/shared/ui/skeleton'

/** «Сравнить все продукты»: table of the full catalog (GET /api/products). */
export function CompareProductsDialog() {
  const productsQuery = useProducts()

  return (
    <Dialog>
      <DialogTrigger render={<Button variant="ghost" size="sm" className="w-full" />}>
        Сравнить все продукты
      </DialogTrigger>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Кредитные продукты Альфа-Банка</DialogTitle>
          <DialogDescription>
            Сравнение условий по всему каталогу. Ставки предварительные, не оферта.
          </DialogDescription>
        </DialogHeader>
        {productsQuery.isLoading ? (
          <div className="flex flex-col gap-2">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : (
          <div className="overflow-x-auto rounded-lg border border-border">
            <table className="w-full text-sm">
              <thead className="bg-bg-secondary">
                <tr>
                  <th className="px-3 py-2 text-left font-bold">Продукт</th>
                  <th className="px-3 py-2 text-left font-bold whitespace-nowrap">Ставка</th>
                  <th className="px-3 py-2 text-left font-bold whitespace-nowrap">Сумма</th>
                  <th className="px-3 py-2 text-left font-bold whitespace-nowrap">Срок</th>
                  <th className="px-3 py-2 text-left font-bold">Особенности</th>
                </tr>
              </thead>
              <tbody>
                {productsQuery.data?.map((product) => (
                  <tr key={product.id} className="border-t border-border/60 align-top">
                    <td className="px-3 py-2 font-medium">{product.name}</td>
                    <td className="px-3 py-2 whitespace-nowrap">{formatRate(product.rate)}</td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {formatMoney(product.minAmount)} — {formatMoney(product.maxAmount)}
                    </td>
                    <td className="px-3 py-2 whitespace-nowrap">
                      {product.minTerm}–{product.maxTerm} мес.
                    </td>
                    <td className="px-3 py-2 text-text-secondary">{product.tagline}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
