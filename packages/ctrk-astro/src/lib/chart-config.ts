/**
 * Chart.js configuration for telemetry visualization
 *
 * Defines channel groupings, colors, axis configurations, and display settings
 * for multi-channel telemetry charts.
 */

/**
 * Telemetry channel definition
 */
export interface ChannelDefinition {
  id: string;
  label: string;
  unit: string;
  color: string;
  yAxisId: string;
  calibrate?: (raw: number) => number; // Optional calibration function
  isBoolean?: boolean; // Boolean channels (rendered as 0/1)
}

/**
 * Channel group definition
 */
export interface ChannelGroup {
  id: string;
  label: string;
  channels: ChannelDefinition[];
  enabled: boolean; // Default enabled state
}

/**
 * Chart color palette (distinct, colorblind-friendly)
 */
export const CHART_COLORS = {
  red: '#e74c3c',
  blue: '#3498db',
  green: '#2ecc71',
  orange: '#e67e22',
  purple: '#9b59b6',
  yellow: '#f1c40f',
  cyan: '#1abc9c',
  pink: '#e91e63',
  teal: '#00bcd4',
  lime: '#8bc34a',
  indigo: '#3f51b5',
  amber: '#ffc107',
  deepOrange: '#ff5722',
  lightGreen: '#4caf50',
  gray: '#95a5a6',
  darkGray: '#7f8c8d',
};

/**
 * Map color palette (distinct colors for laps)
 */
export const MAP_LAP_COLORS = [
  '#e74c3c', // red
  '#3498db', // blue
  '#2ecc71', // green
  '#f39c12', // orange
  '#9b59b6', // purple
  '#1abc9c', // cyan
  '#e91e63', // pink
  '#ff5722', // deep orange
  '#00bcd4', // teal
  '#8bc34a', // lime
  '#ff9800', // amber
  '#673ab7', // deep purple
  '#4caf50', // light green
  '#795548', // brown
  '#607d8b', // blue gray
];

/**
 * Get color for lap number (cycles through palette)
 */
export function getLapColor(lap: number): string {
  return MAP_LAP_COLORS[lap % MAP_LAP_COLORS.length];
}

/**
 * Channel groups for telemetry visualization
 */
export const CHANNEL_GROUPS: ChannelGroup[] = [
  {
    id: 'engine',
    label: 'Engine',
    enabled: true,
    channels: [
      {
        id: 'rpm',
        label: 'RPM',
        unit: 'RPM',
        color: CHART_COLORS.red,
        yAxisId: 'rpm',
      },
      {
        id: 'tps',
        label: 'Throttle (TPS)',
        unit: '%',
        color: CHART_COLORS.orange,
        yAxisId: 'throttle',
      },
      {
        id: 'aps',
        label: 'Throttle (APS)',
        unit: '%',
        color: CHART_COLORS.yellow,
        yAxisId: 'throttle',
      },
      {
        id: 'gear',
        label: 'Gear',
        unit: '',
        color: CHART_COLORS.blue,
        yAxisId: 'gear',
      },
    ],
  },
  {
    id: 'speed',
    label: 'Speed',
    enabled: true,
    channels: [
      {
        id: 'front_speed',
        label: 'Front Speed',
        unit: 'km/h',
        color: CHART_COLORS.blue,
        yAxisId: 'speed',
      },
      {
        id: 'rear_speed',
        label: 'Rear Speed',
        unit: 'km/h',
        color: CHART_COLORS.cyan,
        yAxisId: 'speed',
      },
      {
        id: 'gps_speed_knots',
        label: 'GPS Speed',
        unit: 'km/h',
        color: CHART_COLORS.green,
        yAxisId: 'speed',
      },
    ],
  },
  {
    id: 'chassis',
    label: 'Chassis',
    enabled: true,
    channels: [
      {
        id: 'lean_signed',
        label: 'Lean Angle',
        unit: '°',
        color: CHART_COLORS.purple,
        yAxisId: 'lean',
      },
      {
        id: 'pitch',
        label: 'Pitch Rate',
        unit: '°/s',
        color: CHART_COLORS.pink,
        yAxisId: 'pitch',
      },
    ],
  },
  {
    id: 'acceleration',
    label: 'Acceleration',
    enabled: false,
    channels: [
      {
        id: 'acc_x',
        label: 'Acc X',
        unit: 'G',
        color: CHART_COLORS.red,
        yAxisId: 'acc',
      },
      {
        id: 'acc_y',
        label: 'Acc Y',
        unit: 'G',
        color: CHART_COLORS.blue,
        yAxisId: 'acc',
      },
    ],
  },
  {
    id: 'brakes',
    label: 'Brakes',
    enabled: true,
    channels: [
      {
        id: 'front_brake',
        label: 'Front Brake',
        unit: 'bar',
        color: CHART_COLORS.red,
        yAxisId: 'brake',
      },
      {
        id: 'rear_brake',
        label: 'Rear Brake',
        unit: 'bar',
        color: CHART_COLORS.orange,
        yAxisId: 'brake',
      },
    ],
  },
  {
    id: 'temperature',
    label: 'Temperature',
    enabled: false,
    channels: [
      {
        id: 'water_temp',
        label: 'Water Temp',
        unit: '°C',
        color: CHART_COLORS.blue,
        yAxisId: 'temp',
      },
      {
        id: 'intake_temp',
        label: 'Intake Temp',
        unit: '°C',
        color: CHART_COLORS.orange,
        yAxisId: 'temp',
      },
    ],
  },
  {
    id: 'fuel',
    label: 'Fuel',
    enabled: false,
    channels: [
      {
        id: 'fuel',
        label: 'Fuel',
        unit: 'cc',
        color: CHART_COLORS.green,
        yAxisId: 'fuel',
      },
    ],
  },
  {
    id: 'electronics',
    label: 'Electronics',
    enabled: false,
    channels: [
      {
        id: 'tcs',
        label: 'TCS',
        unit: '',
        color: CHART_COLORS.blue,
        yAxisId: 'bool',
        isBoolean: true,
      },
      {
        id: 'scs',
        label: 'SCS',
        unit: '',
        color: CHART_COLORS.cyan,
        yAxisId: 'bool',
        isBoolean: true,
      },
      {
        id: 'lif',
        label: 'LIF',
        unit: '',
        color: CHART_COLORS.green,
        yAxisId: 'bool',
        isBoolean: true,
      },
      {
        id: 'launch',
        label: 'Launch',
        unit: '',
        color: CHART_COLORS.orange,
        yAxisId: 'bool',
        isBoolean: true,
      },
      {
        id: 'f_abs',
        label: 'F_ABS',
        unit: '',
        color: CHART_COLORS.red,
        yAxisId: 'bool',
        isBoolean: true,
      },
      {
        id: 'r_abs',
        label: 'R_ABS',
        unit: '',
        color: CHART_COLORS.pink,
        yAxisId: 'bool',
        isBoolean: true,
      },
    ],
  },
];

/**
 * Get all channels from a group
 */
export function getChannelsByGroup(groupId: string): ChannelDefinition[] {
  const group = CHANNEL_GROUPS.find((g) => g.id === groupId);
  return group?.channels || [];
}

/**
 * Get all enabled channel groups
 */
export function getEnabledGroups(): ChannelGroup[] {
  return CHANNEL_GROUPS.filter((g) => g.enabled);
}

/**
 * Get all enabled channels (flattened)
 */
export function getEnabledChannels(): ChannelDefinition[] {
  return CHANNEL_GROUPS.filter((g) => g.enabled).flatMap((g) => g.channels);
}

/**
 * Get all channel definitions (flattened from all groups)
 */
export function getAllChannels(): ChannelDefinition[] {
  return CHANNEL_GROUPS.flatMap((g) => g.channels);
}

/**
 * Get default enabled channel IDs (from groups with enabled: true)
 */
export function getDefaultEnabledChannelIds(): string[] {
  return CHANNEL_GROUPS
    .filter((g) => g.enabled)
    .flatMap((g) => g.channels.map((c) => c.id));
}

/**
 * Get all analog (non-boolean) channel IDs from a set of channel IDs
 */
export function filterAnalogChannelIds(channelIds: string[]): string[] {
  const booleanIds = new Set(
    CHANNEL_GROUPS.flatMap((g) => g.channels).filter((c) => c.isBoolean).map((c) => c.id)
  );
  return channelIds.filter((id) => !booleanIds.has(id));
}

/**
 * Get all boolean channel IDs from a set of channel IDs
 */
export function filterBooleanChannelIds(channelIds: string[]): string[] {
  const booleanIds = new Set(
    CHANNEL_GROUPS.flatMap((g) => g.channels).filter((c) => c.isBoolean).map((c) => c.id)
  );
  return channelIds.filter((id) => booleanIds.has(id));
}
