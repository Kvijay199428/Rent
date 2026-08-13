import { useState } from "react";
import PhoneInput from "react-phone-number-input";
import { getCountryCallingCode, type Country } from "react-phone-number-input";
import getCountryFlag from "country-flag-icons/unicode";
import { ChevronDown, Globe } from "lucide-react";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";

interface CountryOption {
  value?: Country;
  label: string;
  divider?: boolean;
}

interface CountrySelectProps {
  value?: Country;
  options: CountryOption[];
  onChange: (value?: Country) => void;
  disabled?: boolean;
  readOnly?: boolean;
  className?: string;
}

function CountrySelect({
  value,
  options,
  onChange,
  disabled,
  readOnly,
  className,
}: CountrySelectProps) {
  const [open, setOpen] = useState(false);
  const selectedCallingCode = value ? getCountryCallingCode(value) : undefined;

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          type="button"
          variant="outline"
          role="combobox"
          aria-expanded={open}
          aria-haspopup="listbox"
          disabled={disabled || readOnly}
          className={cn(
            "h-9 shrink-0 rounded-r-none border-r-0 px-2.5 font-normal text-foreground",
            className
          )}
        >
          <span className="text-base leading-none">
            {value ? (
              getCountryFlag(value)
            ) : (
              <Globe className="size-4" />
            )}
          </span>
          <span className="text-xs tabular-nums">
            {selectedCallingCode ? `+${selectedCallingCode}` : ""}
          </span>
          <ChevronDown className="size-3.5 opacity-50" />
        </Button>
      </PopoverTrigger>
      <PopoverContent align="start" sideOffset={2} className="w-[320px] p-0">
        <Command>
          <CommandInput placeholder="Search country…" />
          <CommandList>
            <CommandEmpty>No country found.</CommandEmpty>
            <CommandGroup>
              {options.map((option) => {
                if (option.divider) return null;
                const isInternational = !option.value;
                return (
                  <CommandItem
                    key={option.value ?? "ZZ"}
                    value={`${option.label} ${option.value ?? ""}`.trim()}
                    onSelect={() => {
                      onChange(isInternational ? undefined : option.value);
                      setOpen(false);
                    }}
                  >
                    <span className="text-base leading-none">
                      {isInternational ? (
                        <Globe className="size-4" />
                      ) : (
                        getCountryFlag(option.value as Country)
                      )}
                    </span>
                    <span className="flex-1 truncate">{option.label}</span>
                    {option.value && (
                      <span className="text-muted-foreground text-xs tabular-nums">
                        +{getCountryCallingCode(option.value)}
                      </span>
                    )}
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </CommandList>
        </Command>
      </PopoverContent>
    </Popover>
  );
}

interface PhoneInputFieldProps {
  value?: string;
  onChange: (value?: string) => void;
  id?: string;
  name?: string;
  placeholder?: string;
  disabled?: boolean;
  readOnly?: boolean;
  autoComplete?: string;
  className?: string;
}

export default function PhoneInputField({
  value,
  onChange,
  className,
  ...props
}: PhoneInputFieldProps) {
  return (
    <PhoneInput
      {...props}
      international
      defaultCountry="IN"
      value={value}
      onChange={onChange}
      inputComponent={Input}
      countrySelectComponent={CountrySelect}
      numberInputProps={{
        className: "flex-1 min-w-0 rounded-l-none",
      }}
      className={cn("flex items-center", className)}
    />
  );
}
