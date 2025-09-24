import { z } from 'zod'

export const TaskTemplateStatusSchema = z.enum(['draft', 'active', 'deprecated'])

export const TaskTemplateInputSchema = z.object({
  name: z.string().min(1, 'Input name is required'),
  type: z.enum(['string', 'number', 'boolean', 'object', 'array']),
  required: z.boolean().default(true),
  default: z.any().optional(),
  description: z.string().default(''),
  validation_rules: z.record(z.any()).default({}),
})

export const TaskTemplateOutputSchema = z.object({
  name: z.string().min(1, 'Output name is required'),
  type: z.string(),
  description: z.string().default(''),
  required: z.boolean().default(true),
  is_file: z.boolean().default(false),
  file_config: z.record(z.any()).nullable().optional(),
})

export const TaskTemplateCreateSchema = z.object({
  name: z.string().min(1).max(255),
  description: z.string().optional(),
  category: z.string().min(1),
  input_schema: z.record(z.any()).default({}),
  output_schema: z.record(z.any()).default({}),
  parameter_schema: z.record(z.any()).default({}),
  required_device_types: z.array(z.string().uuid()).default([]),
  preferred_device_types: z.array(z.string().uuid()).default([]),
  estimated_duration: z.number().positive().optional(),
  max_retries: z.number().min(0).max(10).default(3),
  retry_delay: z.number().min(0).default(60),
  timeout: z.number().positive().optional(),
  requires_user_input: z.boolean().default(false),
  implementation_class: z.string().optional(),
  docker_image: z.string().optional(),
  metadata: z.record(z.any()).default({}),
})

export const TaskTemplateResponseSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  description: z.string().nullable(),
  version: z.string(),
  category: z.string(),
  status: TaskTemplateStatusSchema,
  input_schema: z.record(z.any()),
  output_schema: z.record(z.any()),
  parameter_schema: z.record(z.any()),
  required_device_types: z.array(z.string().uuid()),
  preferred_device_types: z.array(z.string().uuid()),
  estimated_duration: z.number().nullable(),
  max_retries: z.number(),
  retry_delay: z.number(),
  timeout: z.number().nullable(),
  requires_user_input: z.boolean(),
  implementation_class: z.string().nullable(),
  docker_image: z.string().nullable(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  metadata: z.record(z.any()),
})

export const WorkflowStatusSchema = z.enum(['draft', 'active', 'running', 'completed', 'failed', 'cancelled', 'paused'])

export const SampleCreateSchema = z.object({
  name: z.string().min(1).max(255),
  batch_id: z.string().nullable().optional(),
  composition: z.record(z.any()).default({}),
  properties: z.record(z.any()).default({}),
  target_properties: z.record(z.any()).nullable().optional(),
  metadata: z.record(z.any()).default({}),
})

export const SampleResponseSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  workflow_id: z.string().uuid(),
  batch_id: z.string().nullable(),
  composition: z.record(z.any()),
  properties: z.record(z.any()),
  target_properties: z.record(z.any()).nullable(),
  current_task_id: z.string().uuid().nullable(),
  position: z.string().nullable(),
  status: z.string(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  metadata: z.record(z.any()),
})

export const WorkflowCreateSchema = z.object({
  name: z.string().min(1).max(255),
  description: z.string().optional(),
  template_id: z.string().uuid().nullable().optional(),
  task_graph: z.record(z.any()).default({}),
  sample_count: z.number().min(1).max(1000).default(1),
  max_concurrent_tasks: z.number().min(1).max(50).default(5),
  start_conditions: z.record(z.any()).default({}),
  stop_conditions: z.record(z.any()).default({}),
  optimization_targets: z.record(z.any()).nullable().optional(),
  samples: z.array(SampleCreateSchema).default([]),
  metadata: z.record(z.any()).default({}),
})

export const WorkflowResponseSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  description: z.string().nullable(),
  version: z.string(),
  status: WorkflowStatusSchema,
  task_graph: z.record(z.any()),
  sample_count: z.number(),
  max_concurrent_tasks: z.number(),
  start_conditions: z.record(z.any()),
  stop_conditions: z.record(z.any()),
  optimization_targets: z.record(z.any()).nullable(),
  progress_percentage: z.number(),
  current_task_count: z.number(),
  completed_task_count: z.number(),
  started_at: z.string().datetime().nullable(),
  completed_at: z.string().datetime().nullable(),
  estimated_completion: z.string().datetime().nullable(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  metadata: z.record(z.any()),
  template_id: z.string().uuid().nullable(),
})

// Job Types
export const JobStatusSchema = z.enum(['created', 'queued', 'running', 'completed', 'failed', 'cancelled'])

export const JobCreateSchema = z.object({
  workflow_id: z.string().uuid(),
  submitted_by: z.string().optional(),
  priority: z.number().min(1).max(10).default(5),
  max_retries: z.number().min(0).max(10).default(3),
  max_concurrent_tasks: z.number().min(1).max(50).default(5),
  resource_requirements: z.record(z.any()).default({}),
  execution_mode: z.string().default('standard'),
  execution_config: z.record(z.any()).default({}),
  metadata: z.record(z.any()).default({}),
})

export const JobResponseSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  workflow_id: z.string().uuid(),
  submitted_by: z.string().optional(),
  status: JobStatusSchema,
  priority: z.number(),
  max_retries: z.number(),
  max_concurrent_tasks: z.number(),
  resource_requirements: z.record(z.any()),
  execution_mode: z.string(),
  execution_config: z.record(z.any()),
  started_at: z.string().datetime().nullable(),
  completed_at: z.string().datetime().nullable(),
  estimated_completion: z.string().datetime().nullable(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  metadata: z.record(z.any()),
})

// Task Types
export const TaskStatusSchema = z.enum(['pending', 'ready', 'running', 'completed', 'failed', 'cancelled', 'retrying'])

export const TaskResponseSchema = z.object({
  id: z.string().uuid(),
  task_template_id: z.string().uuid(),
  workflow_id: z.string().uuid(),
  job_id: z.string().uuid(),
  status: TaskStatusSchema,
  priority: z.number(),
  retry_count: z.number(),
  inputs: z.record(z.any()),
  outputs: z.record(z.any()).nullable(),
  result_data: z.record(z.any()).nullable(),
  started_at: z.string().datetime().nullable(),
  completed_at: z.string().datetime().nullable(),
  error_message: z.string().nullable(),
  execution_time: z.number().nullable(),
  assigned_device_id: z.string().uuid().nullable(),
  prev_tasks: z.array(z.string()).default([]),
  next_tasks: z.array(z.string()).default([]),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  metadata: z.record(z.any()),
})

// Device Types (assuming basic structure)
export const DeviceResponseSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  device_type_id: z.string().uuid(),
  status: z.string(),
  capabilities: z.record(z.any()),
  location: z.string().optional(),
  created_at: z.string().datetime(),
  updated_at: z.string().datetime(),
  metadata: z.record(z.any()),
})

// Export types
export type TaskTemplateStatus = z.infer<typeof TaskTemplateStatusSchema>
export type TaskTemplateInput = z.infer<typeof TaskTemplateInputSchema>
export type TaskTemplateOutput = z.infer<typeof TaskTemplateOutputSchema>
export type TaskTemplateCreate = z.infer<typeof TaskTemplateCreateSchema>
export type TaskTemplateResponse = z.infer<typeof TaskTemplateResponseSchema>

export type WorkflowStatus = z.infer<typeof WorkflowStatusSchema>
export type SampleCreate = z.infer<typeof SampleCreateSchema>
export type SampleResponse = z.infer<typeof SampleResponseSchema>
export type WorkflowCreate = z.infer<typeof WorkflowCreateSchema>
export type WorkflowResponse = z.infer<typeof WorkflowResponseSchema>

export type JobStatus = z.infer<typeof JobStatusSchema>
export type JobCreate = z.infer<typeof JobCreateSchema>
export type JobResponse = z.infer<typeof JobResponseSchema>

export type TaskStatus = z.infer<typeof TaskStatusSchema>
export type TaskResponse = z.infer<typeof TaskResponseSchema>

export type DeviceResponse = z.infer<typeof DeviceResponseSchema>
