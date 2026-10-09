import type { Meta, StoryObj } from '@storybook/react'
import RiskCard from '../RiskCard'

const meta = {
  title: 'Components/RiskCard',
  component: RiskCard,
  tags: ['autodocs'],
} satisfies Meta<typeof RiskCard>

export default meta
type Story = StoryObj<typeof meta>

export const Default: Story = {
  args: {
    title: 'Suspicious Login',
    risk: 'high',
    description: 'Multiple failed login attempts detected',
  },
}
