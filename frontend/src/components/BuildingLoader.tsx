/**
 * BuildingLoader - Construction-themed loading animation
 * Shows "Your house is building..." with animated crane and stacking bricks
 */
import React from 'react';

export const BuildingLoader = ({ isLoading }: { isLoading: boolean }) => {
  if (!isLoading) return null;

  return (
    <div className="loader-overlay">
      <div className="loader-container">
        {/* Crane tower */}
        <div className="crane-tower">
          <div className="crane-cabin" />
          <div className="crane-counterweight" />
        </div>
        
        {/* Crane arm and hook */}
        <div className="crane-arm-wrapper">
          <div className="crane-arm">
            <div className="hook" />
          </div>
        </div>
        
        {/* Building site with bricks */}
        <div className="building-site">
          <div className="brick brick1"></div>
          <div className="brick brick2"></div>
          <div className="brick brick3"></div>
          <div className="brick brick4"></div>
          <div className="brick brick5"></div>
          <div className="brick-base" />
        </div>
        
        <p className="loading-text">Your house is building</p>
        
        <div className="progress-bar">
          <div className="progress-fill"></div>
        </div>
      </div>
      
      <style>{`
        .loader-overlay {
          position: fixed;
          top: 0;
          left: 0;
          width: 100%;
          height: 100%;
          background: linear-gradient(135deg, rgba(15, 23, 42, 0.95) 0%, rgba(30, 41, 59, 0.98) 100%);
          display: flex;
          justify-content: center;
          align-items: center;
          z-index: 9999;
          backdrop-filter: blur(8px);
        }

        .loader-container {
          background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
          border-radius: 24px;
          padding: 3rem 2.5rem;
          text-align: center;
          box-shadow: 
            0 0 60px rgba(251, 146, 60, 0.3),
            0 25px 50px -12px rgba(0, 0, 0, 0.25);
          width: 320px;
          border: 1px solid rgba(251, 146, 60, 0.2);
        }

        /* Crane Tower */
        .crane-tower {
          position: relative;
          height: 60px;
          width: 12px;
          background: linear-gradient(90deg, #f59e0b 0%, #fbbf24 50%, #f59e0b 100%);
          margin: 0 auto 10px;
          border-radius: 2px;
        }

        .crane-tower::before {
          content: '';
          position: absolute;
          top: -8px;
          left: -4px;
          width: 20px;
          height: 8px;
          background: #f59e0b;
          border-radius: 2px 2px 0 0;
        }

        .crane-cabin {
          position: absolute;
          right: -20px;
          top: 10px;
          width: 16px;
          height: 14px;
          background: #374151;
          border-radius: 2px;
        }

        .crane-counterweight {
          position: absolute;
          left: -12px;
          top: 35px;
          width: 20px;
          height: 10px;
          background: #6b7280;
          border-radius: 2px;
        }

        /* Crane Arm */
        .crane-arm-wrapper {
          position: relative;
          height: 30px;
          margin-bottom: 20px;
        }

        .crane-arm {
          width: 140px;
          height: 6px;
          background: linear-gradient(180deg, #f59e0b 0%, #d97706 100%);
          margin: 0 auto;
          position: relative;
          animation: swing 2.5s ease-in-out infinite alternate;
          border-radius: 3px;
        }

        .hook {
          width: 10px;
          height: 24px;
          background: linear-gradient(180deg, #6b7280 0%, #4b5563 100%);
          margin: -24px auto 0;
          position: relative;
          border-radius: 0 0 3px 3px;
          animation: lift 2.5s ease-in-out infinite alternate;
        }

        @keyframes swing {
          0% { transform: translateX(-50%) rotate(-3deg); transform-origin: center; }
          100% { transform: translateX(-50%) rotate(3deg); transform-origin: center; }
        }

        @keyframes lift {
          0% { transform: translateY(0); }
          100% { transform: translateY(-12px); }
        }

        /* Building Site */
        .building-site {
          height: 80px;
          display: flex;
          justify-content: center;
          align-items: flex-end;
          gap: 4px;
          margin-bottom: 20px;
        }

        .brick-base {
          width: 80px;
          height: 8px;
          background: linear-gradient(180deg, #64748b 0%, #475569 100%);
          border-radius: 2px;
          margin-right: 40px;
        }

        .brick {
          width: 28px;
          height: 16px;
          background: linear-gradient(180deg, #dc2626 0%, #b91c1c 100%);
          border-radius: 2px;
          opacity: 0;
          position: relative;
        }

        .brick1 { animation: stackUp 3s 0s infinite; margin-bottom: 0; }
        .brick2 { animation: stackUp 3s 0.5s infinite; margin-bottom: 16px; }
        .brick3 { animation: stackUp 3s 1s infinite; margin-bottom: 32px; }
        .brick4 { animation: stackUp 3s 1.5s infinite; margin-bottom: 48px; }
        .brick5 { animation: stackUp 3s 2s infinite; margin-bottom: 64px; }

        @keyframes stackUp {
          0% { 
            opacity: 0; 
            transform: translateY(-30px) scale(0.8); 
          }
          15% { 
            opacity: 1; 
            transform: translateY(0) scale(1); 
          }
          85% { 
            opacity: 1; 
            transform: translateY(0) scale(1); 
          }
          100% { 
            opacity: 0; 
            transform: translateY(-30px) scale(0.8); 
          }
        }

        .loading-text {
          font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          font-weight: 700;
          font-size: 1.3rem;
          color: #1e293b;
          margin-bottom: 20px;
          letter-spacing: -0.02em;
          animation: pulse 1.5s ease-in-out infinite;
        }

        @keyframes pulse {
          0%, 100% { transform: scale(1); }
          50% { transform: scale(1.03); }
        }

        /* Progress Bar */
        .progress-bar {
          width: 100%;
          height: 6px;
          background: #e2e8f0;
          border-radius: 3px;
          overflow: hidden;
        }

        .progress-fill {
          width: 0%;
          height: 100%;
          background: linear-gradient(90deg, #f59e0b 0%, #f97316 50%, #f59e0b 100%);
          animation: fillProgress 3s ease-in-out infinite;
          border-radius: 3px;
        }

        @keyframes fillProgress {
          0% { width: 0%; }
          50% { width: 75%; }
          100% { width: 100%; }
        }
      `}</style>
    </div>
  );
};

export default BuildingLoader;