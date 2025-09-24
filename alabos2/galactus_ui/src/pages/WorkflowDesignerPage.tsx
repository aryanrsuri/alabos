import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'

export function WorkflowDesignerPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Workflow Designer</h1>
          <p className="mt-2 text-gray-600">
            Design complex laboratory workflows with visual tools
          </p>
        </div>
        <Button>
          Save Workflow
        </Button>
      </div>

      <Card className="p-12 text-center">
        <h3 className="text-lg font-medium text-gray-900">Visual Workflow Designer</h3>
        <p className="mt-2 text-gray-500">
          This feature is under development. The workflow designer will include a drag-and-drop interface for creating task graphs, sample matrix definition, and optimization target configuration.
        </p>
      </Card>
    </div>
  )
}
