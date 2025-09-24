import { useState, useEffect } from 'react'
import { useForm, useFieldArray } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Plus, Minus, Save, ArrowLeft } from 'lucide-react'
import { apiClient } from '@/services/api'
import { TaskTemplateCreate, TaskTemplateResponse, TaskTemplateCreateSchema } from '@/types/api'
import { Button } from '@/components/ui/Button'
import { Card } from '@/components/ui/Card'

interface FormData extends Omit<TaskTemplateCreate, 'required_device_types' | 'preferred_device_types'> {
  required_device_types: string[]
  preferred_device_types: string[]
}

const categories = [
  'synthesis',
  'characterization',
  'analysis',
  'measurement',
  'preparation',
  'processing',
  'testing',
  'quality_control',
]

export function TaskTemplateBuilderPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const isEditing = Boolean(id)

  const [activeTab, setActiveTab] = useState<'basic' | 'inputs' | 'outputs' | 'parameters'>('basic')

  const { data: template } = useQuery({
    queryKey: ['task-template', id],
    queryFn: () => apiClient.getTaskTemplate(id!),
    enabled: isEditing,
  })

  const { register, control, handleSubmit, watch, setValue, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(TaskTemplateCreateSchema),
    defaultValues: {
      name: '',
      description: '',
      category: 'analysis',
      input_schema: {},
      output_schema: {},
      parameter_schema: {},
      required_device_types: [],
      preferred_device_types: [],
      estimated_duration: undefined,
      max_retries: 3,
      retry_delay: 60,
      timeout: undefined,
      requires_user_input: false,
      implementation_class: '',
      docker_image: '',
      metadata: {},
    },
  })

  const {
    fields: inputFields,
    append: appendInput,
    remove: removeInput,
  } = useFieldArray({
    control,
    name: 'input_schema',
  })

  const {
    fields: outputFields,
    append: appendOutput,
    remove: removeOutput,
  } = useFieldArray({
    control,
    name: 'output_schema',
  })

  const createMutation = useMutation({
    mutationFn: (data: TaskTemplateCreate) => apiClient.createTaskTemplate(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task-templates'] })
      navigate('/task-templates')
    },
  })

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: TaskTemplateCreate }) =>
      apiClient.updateTaskTemplate(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task-templates'] })
      queryClient.invalidateQueries({ queryKey: ['task-template', id] })
      navigate('/task-templates')
    },
  })

  useEffect(() => {
    if (template && isEditing) {
      setValue('name', template.name)
      setValue('description', template.description || '')
      setValue('category', template.category)
      setValue('input_schema', template.input_schema)
      setValue('output_schema', template.output_schema)
      setValue('parameter_schema', template.parameter_schema)
      setValue('required_device_types', template.required_device_types)
      setValue('preferred_device_types', template.preferred_device_types)
      setValue('estimated_duration', template.estimated_duration || undefined)
      setValue('max_retries', template.max_retries)
      setValue('retry_delay', template.retry_delay)
      setValue('timeout', template.timeout || undefined)
      setValue('requires_user_input', template.requires_user_input)
      setValue('implementation_class', template.implementation_class || '')
      setValue('docker_image', template.docker_image || '')
      setValue('metadata', template.metadata)
    }
  }, [template, isEditing, setValue])

  const onSubmit = (data: FormData) => {
    const submitData: TaskTemplateCreate = {
      ...data,
      required_device_types: data.required_device_types.filter(Boolean),
      preferred_device_types: data.preferred_device_types.filter(Boolean),
    }

    if (isEditing) {
      updateMutation.mutate({ id: id!, data: submitData })
    } else {
      createMutation.mutate(submitData)
    }
  }

  const tabs = [
    { id: 'basic', name: 'Basic Info', icon: '📝' },
    { id: 'inputs', name: 'Inputs', icon: '📥' },
    { id: 'outputs', name: 'Outputs', icon: '📤' },
    { id: 'parameters', name: 'Parameters', icon: '⚙️' },
  ]

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Button variant="outline" onClick={() => navigate('/task-templates')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
          <div>
            <h1 className="text-3xl font-bold text-gray-900">
              {isEditing ? 'Edit Task Template' : 'Create Task Template'}
            </h1>
            <p className="mt-2 text-gray-600">
              {isEditing ? 'Modify the task template configuration' : 'Define a new reusable task template'}
            </p>
          </div>
        </div>
        <Button
          onClick={handleSubmit(onSubmit)}
          disabled={createMutation.isPending || updateMutation.isPending}
        >
          <Save className="mr-2 h-4 w-4" />
          {createMutation.isPending || updateMutation.isPending ? 'Saving...' : 'Save Template'}
        </Button>
      </div>

      {/* Tab Navigation */}
      <div className="border-b border-gray-200">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id as any)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Basic Info Tab */}
        {activeTab === 'basic' && (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <Card className="p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Basic Information</h3>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Template Name *
                  </label>
                  <input
                    {...register('name')}
                    type="text"
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                    placeholder="e.g., XRD Analysis"
                  />
                  {errors.name && (
                    <p className="mt-1 text-sm text-red-600">{errors.name.message}</p>
                  )}
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Description
                  </label>
                  <textarea
                    {...register('description')}
                    rows={3}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                    placeholder="Describe what this task template does..."
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Category *
                  </label>
                  <select
                    {...register('category')}
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                  >
                    {categories.map(category => (
                      <option key={category} value={category}>
                        {category.charAt(0).toUpperCase() + category.slice(1).replace('_', ' ')}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </Card>

            <Card className="p-6">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Execution Settings</h3>
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Max Retries
                    </label>
                    <input
                      {...register('max_retries', { valueAsNumber: true })}
                      type="number"
                      min="0"
                      max="10"
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700">
                      Retry Delay (seconds)
                    </label>
                    <input
                      {...register('retry_delay', { valueAsNumber: true })}
                      type="number"
                      min="0"
                      className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Estimated Duration (seconds)
                  </label>
                  <input
                    {...register('estimated_duration', { valueAsNumber: true })}
                    type="number"
                    min="1"
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700">
                    Timeout (seconds)
                  </label>
                  <input
                    {...register('timeout', { valueAsNumber: true })}
                    type="number"
                    min="1"
                    className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                  />
                </div>

                <div className="flex items-center">
                  <input
                    {...register('requires_user_input')}
                    type="checkbox"
                    className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                  />
                  <label className="ml-2 block text-sm text-gray-900">
                    Requires user input during execution
                  </label>
                </div>
              </div>
            </Card>
          </div>
        )}

        {/* Inputs Tab */}
        {activeTab === 'inputs' && (
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">Input Schema</h3>
              <Button
                type="button"
                variant="outline"
                onClick={() => appendInput({ name: '', type: 'string', required: true })}
              >
                <Plus className="mr-2 h-4 w-4" />
                Add Input
              </Button>
            </div>

            <div className="space-y-4">
              {inputFields.map((field, index) => (
                <div key={field.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Name *
                      </label>
                      <input
                        {...register(`input_schema.${index}.name`)}
                        type="text"
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Type *
                      </label>
                      <select
                        {...register(`input_schema.${index}.type`)}
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                      >
                        <option value="string">String</option>
                        <option value="number">Number</option>
                        <option value="boolean">Boolean</option>
                        <option value="object">Object</option>
                        <option value="array">Array</option>
                      </select>
                    </div>

                    <div className="flex items-center">
                      <input
                        {...register(`input_schema.${index}.required`)}
                        type="checkbox"
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                      />
                      <label className="ml-2 block text-sm text-gray-900">
                        Required
                      </label>
                    </div>

                    <div className="flex items-end">
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => removeInput(index)}
                        className="text-red-600 hover:text-red-700"
                      >
                        <Minus className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Outputs Tab */}
        {activeTab === 'outputs' && (
          <Card className="p-6">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-medium text-gray-900">Output Schema</h3>
              <Button
                type="button"
                variant="outline"
                onClick={() => appendOutput({ name: '', type: 'string' })}
              >
                <Plus className="mr-2 h-4 w-4" />
                Add Output
              </Button>
            </div>

            <div className="space-y-4">
              {outputFields.map((field, index) => (
                <div key={field.id} className="border border-gray-200 rounded-lg p-4">
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Name *
                      </label>
                      <input
                        {...register(`output_schema.${index}.name`)}
                        type="text"
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700">
                        Type *
                      </label>
                      <select
                        {...register(`output_schema.${index}.type`)}
                        className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                      >
                        <option value="string">String</option>
                        <option value="number">Number</option>
                        <option value="boolean">Boolean</option>
                        <option value="object">Object</option>
                        <option value="array">Array</option>
                        <option value="file">File</option>
                      </select>
                    </div>

                    <div className="flex items-center">
                      <input
                        {...register(`output_schema.${index}.required`)}
                        type="checkbox"
                        className="h-4 w-4 text-primary-600 focus:ring-primary-500 border-gray-300 rounded"
                      />
                      <label className="ml-2 block text-sm text-gray-900">
                        Required
                      </label>
                    </div>

                    <div className="flex items-end">
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => removeOutput(index)}
                        className="text-red-600 hover:text-red-700"
                      >
                        <Minus className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        {/* Parameters Tab */}
        {activeTab === 'parameters' && (
          <Card className="p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Implementation Details</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Implementation Class
                </label>
                <input
                  {...register('implementation_class')}
                  type="text"
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                  placeholder="e.g., mylab.tasks.XRDTask"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Docker Image
                </label>
                <input
                  {...register('docker_image')}
                  type="text"
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                  placeholder="e.g., mylab/xrd-analysis:latest"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700">
                  Metadata (JSON)
                </label>
                <textarea
                  {...register('metadata')}
                  rows={4}
                  className="mt-1 block w-full border-gray-300 rounded-md shadow-sm focus:ring-primary-500 focus:border-primary-500"
                  placeholder='{"author": "John Doe", "version": "1.0"}'
                />
              </div>
            </div>
          </Card>
        )}
      </form>
    </div>
  )
}
