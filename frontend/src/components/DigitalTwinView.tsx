import React from 'react';
import { FutureOutlookView } from './FutureOutlookView';
import { TwinState, Measurement, Forecast } from '../types';

interface DigitalTwinViewProps {
  patientId: string;
  twinState: TwinState | null;
  measurements: Measurement[];
  forecasts: Forecast[];
  onRefreshData: () => void;
}

export const DigitalTwinView: React.FC<DigitalTwinViewProps> = ({
  patientId,
  twinState,
  measurements,
  forecasts,
  onRefreshData,
}) => {
  return (
    <div className="space-y-6">
      <FutureOutlookView
        patientId={patientId}
        twinState={twinState}
        measurements={measurements}
        forecasts={forecasts}
        onRefreshData={onRefreshData}
      />
    </div>
  );
};
