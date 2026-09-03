import { useState } from 'react';
import { StructuredAddress, EMPTY_ADDRESS } from './address';
import { COUNTRY_OPTIONS, getCountryName } from './countries';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover';
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command';
import getCountryFlag from 'country-flag-icons/unicode';
import { ChevronDown, Globe } from 'lucide-react';
import { cn } from '@/lib/utils';

interface CountrySelectProps {
  value: string;
  onSelect: (code: string) => void;
  idPrefix: string;
}

function CountrySelect({ value, onSelect, idPrefix }: CountrySelectProps) {
  const [open, setOpen] = useState(false);
  const name = getCountryName(value);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          role="combobox"
          aria-expanded={open}
          aria-haspopup="listbox"
          variant="outline"
          id={`${idPrefix}-country`}
          className="w-full justify-between font-normal text-foreground"
        >
          <span className="flex min-w-0 items-center gap-2">
            {value ? (
              <span className="text-base leading-none shrink-0">
                {getCountryFlag(value)}
              </span>
            ) : (
              <Globe className="size-4 shrink-0 text-muted-foreground" />
            )}
            <span className="truncate">{name || 'Select country…'}</span>
          </span>
          <ChevronDown className="size-3.5 shrink-0 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" sideOffset={2} className="w-[320px] p-0">
        <Command>
          <CommandInput placeholder="Search country…" />
          <CommandList>
            <CommandEmpty>No country found.</CommandEmpty>
            <CommandGroup>
              {COUNTRY_OPTIONS.map((option) => (
                <CommandItem
                  key={option.code}
                  value={`${option.name} ${option.code}`}
                  onSelect={() => {
                    onSelect(option.code);
                    setOpen(false);
                  }}
                >
                  <span className="text-base leading-none">
                    {getCountryFlag(option.code)}
                  </span>
                  <span className="flex-1 truncate">{option.name}</span>
                  <span className="text-muted-foreground text-xs">
                    {option.code}
                  </span>
                </CommandItem>
              ))}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

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
        <Label>Country</Label>
        <CountrySelect
          value={country ?? value.country ?? ''}
          onSelect={(code) => set('country', code)}
          idPrefix={idPrefix}
        />
      </div>
    </div>
  );
}
