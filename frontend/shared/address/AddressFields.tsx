import { StructuredAddress, EMPTY_ADDRESS } from './address';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { cn } from '@/lib/utils';

interface AddressFieldsProps {
  value?: StructuredAddress;
  onChange: (value: StructuredAddress) => void;
  country?: string;
  idPrefix?: string;
  className?: string;
}

export default function AddressFields({
  value = EMPTY_ADDRESS,
  onChange,
  country,
  idPrefix = 'address',
  className,
}: AddressFieldsProps) {
  const set = (field: keyof StructuredAddress, v: string) => {
    onChange({ ...value, [field]: v });
  };

  return (
    <div className={cn('grid grid-cols-1 sm:grid-cols-2 gap-3', className)}>
      <div className="space-y-2 sm:col-span-2">
        <Label htmlFor={`${idPrefix}-flatNo`}>Flat / House No</Label>
        <Input
          id={`${idPrefix}-flatNo`}
          placeholder="e.g. 304, B Wing"
          value={value.flatNo ?? ''}
          onChange={(e) => set('flatNo', e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}-floor`}>Floor</Label>
        <Input
          id={`${idPrefix}-floor`}
          placeholder="e.g. 3rd"
          value={value.floor ?? ''}
          onChange={(e) => set('floor', e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}-block`}>Block</Label>
        <Input
          id={`${idPrefix}-block`}
          placeholder="e.g. B"
          value={value.block ?? ''}
          onChange={(e) => set('block', e.target.value)}
        />
      </div>

      <div className="space-y-2 sm:col-span-2">
        <Label htmlFor={`${idPrefix}-street`}>Street / Road</Label>
        <Input
          id={`${idPrefix}-street`}
          placeholder="e.g. MG Road"
          value={value.street ?? ''}
          onChange={(e) => set('street', e.target.value)}
        />
      </div>

      <div className="space-y-2 sm:col-span-2">
        <Label htmlFor={`${idPrefix}-locality`}>Area / Locality / Village</Label>
        <Input
          id={`${idPrefix}-locality`}
          placeholder="e.g. Indiranagar"
          value={value.locality ?? ''}
          onChange={(e) => set('locality', e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}-city`}>City / Town</Label>
        <Input
          id={`${idPrefix}-city`}
          placeholder="e.g. Bengaluru"
          value={value.city ?? ''}
          onChange={(e) => set('city', e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}-state`}>State</Label>
        <Input
          id={`${idPrefix}-state`}
          placeholder="e.g. Karnataka"
          value={value.state ?? ''}
          onChange={(e) => set('state', e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}-pinCode`}>PIN Code</Label>
        <Input
          id={`${idPrefix}-pinCode`}
          placeholder="e.g. 560001"
          value={value.pinCode ?? ''}
          onChange={(e) => set('pinCode', e.target.value)}
          inputMode="numeric"
          maxLength={10}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor={`${idPrefix}-country`}>Country</Label>
        <Input
          id={`${idPrefix}-country`}
          value={country ?? value.country ?? ''}
          readOnly
          disabled
          placeholder="Detecting…"
        />
      </div>
    </div>
  );
}
