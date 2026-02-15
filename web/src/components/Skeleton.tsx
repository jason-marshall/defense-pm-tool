import type { CSSProperties } from 'react';

interface SkeletonProps {
  className?: string;
  variant?: 'text' | 'circular' | 'rectangular';
  width?: string | number;
  height?: string | number;
}

export const Skeleton = ({
  className = '',
  variant = 'rectangular',
  width,
  height,
}: SkeletonProps) => {
  const baseStyles = 'animate-pulse bg-gray-200';

  const variantStyles = {
    text: 'rounded',
    circular: 'rounded-full',
    rectangular: 'rounded-md',
  };

  const style: CSSProperties = {
    width: width,
    height: height,
  };

  return (
    <div
      className={`${baseStyles} ${variantStyles[variant]} ${className}`}
      style={style}
      role="status"
      aria-label="Loading..."
    />
  );
};

// Pre-built skeleton patterns
export const TableSkeleton = ({ rows = 5 }: { rows?: number }) => (
  <div className="space-y-3">
    {Array.from({ length: rows }).map((_, i) => (
      <div key={i} className="flex gap-4">
        <Skeleton width="20%" height={20} />
        <Skeleton width="30%" height={20} />
        <Skeleton width="25%" height={20} />
        <Skeleton width="15%" height={20} />
      </div>
    ))}
  </div>
);

export const CardSkeleton = () => (
  <div className="p-6 border rounded-lg space-y-4">
    <Skeleton width="60%" height={24} />
    <Skeleton width="100%" height={16} />
    <Skeleton width="80%" height={16} />
    <div className="flex gap-2 pt-2">
      <Skeleton width={80} height={32} />
      <Skeleton width={80} height={32} />
    </div>
  </div>
);

export const DashboardSkeleton = () => (
  <div className="space-y-6">
    <div className="grid grid-cols-4 gap-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="p-4 border rounded-lg">
          <Skeleton width="50%" height={16} className="mb-2" />
          <Skeleton width="80%" height={32} />
        </div>
      ))}
    </div>
    <div className="grid grid-cols-2 gap-6">
      <Skeleton height={300} />
      <Skeleton height={300} />
    </div>
  </div>
);

export const MetricCardSkeleton = () => (
  <div className="p-4 border rounded-lg bg-white shadow-xs">
    <Skeleton width="40%" height={14} className="mb-2" />
    <Skeleton width="60%" height={28} className="mb-1" />
    <Skeleton width="30%" height={12} />
  </div>
);

export const ChartSkeleton = ({ height = 300 }: { height?: number }) => (
  <div className="p-4 border rounded-lg bg-white">
    <Skeleton width="30%" height={20} className="mb-4" />
    <Skeleton width="100%" height={height} />
  </div>
);
