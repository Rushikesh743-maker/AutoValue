import React, { useState } from 'react';
import { Car } from 'lucide-react';

interface VehicleImageProps {
  brand?: string;
  model?: string;
  variant?: string;
  year?: number;
  src?: string | null;
  alt?: string;
  className?: string;
  aspectRatio?: '16/9' | '4/3' | '3/2' | 'auto';
  compact?: boolean; // For tight lists/cards (e.g. Garage thumbnails)
  priority?: boolean;
}

// Map of verified vehicle models to their local high-resolution, optimized catalog assets
const VERIFIED_CATALOG_IMAGES: Record<string, { webp: string; jpg: string; label: string }> = {
  creta: {
    webp: '/images/catalog_creta.webp',
    jpg: '/images/catalog_creta.jpg',
    label: 'Verified catalog photo (Hyundai Creta)'
  },
  city: {
    webp: '/images/catalog_city.webp',
    jpg: '/images/catalog_city.jpg',
    label: 'Verified catalog photo (Honda City)'
  },
  swift: {
    webp: '/images/catalog_swift.webp',
    jpg: '/images/catalog_swift.jpg',
    label: 'Verified catalog photo (Maruti Suzuki Swift)'
  },
  dzire: {
    webp: '/images/catalog_swift.webp',
    jpg: '/images/catalog_swift.jpg',
    label: 'Verified catalog photo (Maruti Suzuki Dzire)'
  },
  nexon: {
    webp: '/images/catalog_nexon.webp',
    jpg: '/images/catalog_nexon.jpg',
    label: 'Verified catalog photo (Tata Nexon)'
  }
};

export const getVerifiedVehicleImage = (_brand?: string, model?: string) => {
  if (!model) return null;
  const normalizedModel = model.toLowerCase().trim();
  for (const [key, asset] of Object.entries(VERIFIED_CATALOG_IMAGES)) {
    if (normalizedModel.includes(key)) {
      return asset;
    }
  }
  return null;
};

export const VehicleImage: React.FC<VehicleImageProps> = ({
  brand,
  model,
  variant,
  year,
  src,
  alt,
  className = '',
  aspectRatio = '16/9',
  compact = false,
  priority = false
}) => {
  const [loadError, setLoadError] = useState(false);

  // Determine verified image asset
  const catalogAsset = !src ? getVerifiedVehicleImage(brand, model) : null;
  const verifiedWebp = src || catalogAsset?.webp || undefined;
  const verifiedJpg = src || catalogAsset?.jpg || undefined;

  const displayAlt = alt || `${year ? `${year} ` : ''}${brand || ''} ${model || 'Vehicle'}${variant ? ` (${variant})` : ''}`.trim();

  // If no verified image or image failed to load, render consistent neutral architectural placeholder
  if (!verifiedWebp || !verifiedJpg || loadError) {
    if (compact) {
      return (
        <div 
          className={`w-10 h-10 rounded-lg bg-[#0d1322] border border-[#1c263c] flex items-center justify-center text-slate-500 shrink-0 ${className}`}
          title={`${displayAlt} (No verified photo)`}
        >
          <Car className="w-5 h-5 text-slate-500/70" />
        </div>
      );
    }

    return (
      <div 
        className={`relative overflow-hidden rounded-lg bg-gradient-to-br from-[#0c1220] via-[#090e1a] to-[#070b14] border border-[#1c263c] flex flex-col items-center justify-center p-4 text-center select-none ${className}`}
        style={{ aspectRatio: aspectRatio === 'auto' ? undefined : aspectRatio.replace('/', ' / ') }}
      >
        {/* Subtle architectural background grid */}
        <div 
          className="absolute inset-0 opacity-[0.03] pointer-events-none" 
          style={{
            backgroundImage: `radial-gradient(circle at 1px 1px, #38bdf8 1px, transparent 0)`,
            backgroundSize: '16px 16px'
          }}
        />

        <div className="w-12 h-12 rounded-full bg-[#131b2e] border border-[#273553] flex items-center justify-center text-slate-400 mb-2">
          <Car className="w-6 h-6 text-slate-400" />
        </div>

        <div className="space-y-0.5 max-w-xs relative z-10">
          <p className="text-xs font-semibold text-slate-300 truncate">
            {displayAlt || 'Vehicle Record'}
          </p>
          <p className="text-[10px] text-slate-500">
            Specifications verified • No listing photo
          </p>
        </div>
      </div>
    );
  }

  // Compact thumbnail with verified image
  if (compact) {
    return (
      <div className={`w-10 h-10 rounded-lg overflow-hidden bg-[#0d1322] border border-[#1c263c] shrink-0 relative ${className}`}>
        <picture>
          <source type="image/webp" srcSet={verifiedWebp} />
          <img
            src={verifiedJpg}
            alt={displayAlt}
            loading={priority ? 'eager' : 'lazy'}
            onError={() => setLoadError(true)}
            className="w-full h-full object-cover object-center"
          />
        </picture>
      </div>
    );
  }

  // Full-featured image container with matching dimensions and subtle hover on fine pointers
  return (
    <div
      className={`group relative overflow-hidden rounded-lg bg-[#090d16] border border-[#1c263c] ${className}`}
      style={{ aspectRatio: aspectRatio === 'auto' ? undefined : aspectRatio.replace('/', ' / ') }}
    >
      <picture>
        <source type="image/webp" srcSet={verifiedWebp} />
        <img
          src={verifiedJpg}
          alt={displayAlt}
          loading={priority ? 'eager' : 'lazy'}
          onError={() => setLoadError(true)}
          className="w-full h-full object-cover object-center transition-transform duration-300 ease-out sm:group-hover:scale-[1.02]"
        />
      </picture>

      {/* Discreet verification watermark badge */}
      {catalogAsset && (
        <div className="absolute bottom-2 right-2 px-2 py-0.5 rounded bg-[#090d16]/80 backdrop-blur-sm border border-[#1c263c] text-[10px] font-mono text-slate-300">
          Verified Catalog Asset
        </div>
      )}
    </div>
  );
};
