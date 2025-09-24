import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'

export function WorkflowsPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Workflows</h1>
          <p className="mt-2 text-gray-600">
            Manage your laboratory workflows and experiments
          </p>
        </div>
        <Button>
          New Workflow
        </Button>
      </div>

      <Card className="p-12 text-center">
        <h3 className="text-lg font-medium text-gray-900">Workflow Management</h3>
        <p className="mt-2 text-gray-500">
          This feature is under development. The workflow designer will allow you to create complex experimental workflows with drag-and-drop task arrangement and sample management.
        </p>
      </Card>
    </div>
  )
}
