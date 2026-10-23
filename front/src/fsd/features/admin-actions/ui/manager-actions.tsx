'use client'

import { useState } from 'react'

import type { Application } from '@/fsd/entities/application/model/schemas'
import {
  ASSIGN_ANALYST_STATUSES,
  MANAGER_ACTION_STATUSES,
} from '@/fsd/entities/application/model/status-labels'
import {
  useAssignAnalyst,
  useRequestInfo,
} from '@/fsd/features/admin-actions/model/use-admin-actions'
import { Button } from '@/fsd/shared/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/fsd/shared/ui/dialog'
import { Textarea } from '@/fsd/shared/ui/textarea'

const MESSAGE_MIN = 3
const MESSAGE_MAX = 1000

function RequestInfoDialog({
  applicationId,
  open,
  onClose,
}: {
  applicationId: number
  open: boolean
  onClose: () => void
}) {
  const requestInfo = useRequestInfo(applicationId)
  const [message, setMessage] = useState('')

  const isValid = message.trim().length >= MESSAGE_MIN

  const handleSubmit = () => {
    if (!isValid) return
    requestInfo.mutate(message.trim(), { onSuccess: onClose })
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Запросить уточнения</DialogTitle>
          <DialogDescription>
            Текст запроса увидит клиент в карточке заявки (статус «Нужны данные»).
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-2">
          <Textarea
            rows={4}
            value={message}
            onChange={(e) => setMessage(e.target.value.slice(0, MESSAGE_MAX))}
            placeholder="Что именно нужно уточнить у клиента"
          />
          <span className="text-right text-[11px] text-text-secondary">
            {message.trim().length}/{MESSAGE_MAX} (минимум {MESSAGE_MIN})
          </span>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={onClose} disabled={requestInfo.isPending}>
              Отмена
            </Button>
            <Button size="sm" onClick={handleSubmit} disabled={!isValid || requestInfo.isPending}>
              {requestInfo.isPending ? 'Отправляем…' : 'Отправить запрос'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function AssignAnalystDialog({
  applicationId,
  open,
  onClose,
}: {
  applicationId: number
  open: boolean
  onClose: () => void
}) {
  const assignAnalyst = useAssignAnalyst(applicationId)

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Передать аналитику</DialogTitle>
          <DialogDescription>
            Заявка перейдёт в статус «Ручная экспертиза» — решение примет кредитный аналитик.
          </DialogDescription>
        </DialogHeader>
        <div className="flex justify-end gap-2">
          <Button variant="ghost" size="sm" onClick={onClose} disabled={assignAnalyst.isPending}>
            Отмена
          </Button>
          <Button
            size="sm"
            onClick={() => assignAnalyst.mutate(undefined, { onSuccess: onClose })}
            disabled={assignAnalyst.isPending}
          >
            {assignAnalyst.isPending ? 'Передаём…' : 'Передать аналитику'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  )
}

/** bank_manager actions (data_check/scoring/manual_review). */
export function ManagerActions({ application }: { application: Application }) {
  const [requestOpen, setRequestOpen] = useState(false)
  const [assignOpen, setAssignOpen] = useState(false)

  if (!MANAGER_ACTION_STATUSES.includes(application.status)) return null

  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs font-bold tracking-wider text-text-secondary uppercase">
        Действия менеджера
      </p>
      <div className="flex gap-2">
        <Button size="sm" onClick={() => setRequestOpen(true)}>
          Запросить уточнения
        </Button>
        {ASSIGN_ANALYST_STATUSES.includes(application.status) && (
          <Button size="sm" variant="outline" onClick={() => setAssignOpen(true)}>
            Передать аналитику
          </Button>
        )}
      </div>
      {requestOpen && (
        <RequestInfoDialog
          applicationId={application.id}
          open={requestOpen}
          onClose={() => setRequestOpen(false)}
        />
      )}
      {assignOpen && (
        <AssignAnalystDialog
          applicationId={application.id}
          open={assignOpen}
          onClose={() => setAssignOpen(false)}
        />
      )}
    </div>
  )
}
