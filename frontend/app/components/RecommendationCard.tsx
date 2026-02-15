import { CommunitySource } from '../lib/types';
import { useState } from 'react';

interface RecommendationCardProps {
  recommendation: string;
  communitySources: CommunitySource[];
}

export default function RecommendationCard({
  recommendation,
  communitySources,
}: RecommendationCardProps) {
  const [showSources, setShowSources] = useState(false);

  return (
    <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg mb-5">
      <div className="flex items-start gap-2 mb-2">
        <div className="text-blue-600 text-lg leading-none mt-0.5">*</div>
        <div>
          <div className="text-sm font-semibold text-blue-900 mb-1">Parts Advisor</div>
          <div className="text-sm text-blue-800 leading-relaxed">{recommendation}</div>
        </div>
      </div>

      {communitySources.length > 0 && (
        <div className="mt-3 pt-2 border-t border-blue-200">
          <button
            onClick={() => setShowSources(!showSources)}
            className="text-xs text-blue-600 hover:text-blue-800 cursor-pointer bg-transparent border-none p-0 underline"
          >
            {showSources ? 'Hide' : 'Show'} community sources ({communitySources.length})
          </button>
          {showSources && (
            <div className="mt-2 space-y-1.5">
              {communitySources.map((source, i) => (
                <a
                  key={i}
                  href={source.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="block text-xs text-blue-700 hover:text-blue-900 no-underline"
                >
                  <span className="text-gray-400 mr-1">{source.source}</span>
                  {source.title}
                  {source.score > 0 && (
                    <span className="text-gray-400 ml-1">({source.score} pts)</span>
                  )}
                </a>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
