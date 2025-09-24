import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'

export function DevicesPage() {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Devices</h1>
          <p className="mt-2 text-gray-600">
            Manage laboratory devices and equipment
          </p>
        </div>
        <Button>
          Add Device
        </Button>
      </div>

      <Card className="p-12 text-center">
        <h3 className="text-lg font-medium text-gray-900">Device Management</h3>
        <p className="mt-2 text-gray-500">
          This feature is under development. Device management will include device registration, status monitoring, and capability management.
        </p>
      </Card>
    </div>
  )
}
