The modal needs two exclusive modes: **viewer mode** and **upload mode**. Currently the upload form is conditionally added above the viewer, but the occupant list and preview panes are always rendered afterward—so they remain visible. The close icon is also absolutely positioned at `top-4 right-4`, which collides with the header’s right-side `Cancel Upload` button.  

## Fix layout behavior

In `OccupantsModal.tsx`, make `isUploading` the single source of truth:

```tsx
const [isUploading, setIsUploading] = useState(false);
```

When the modal closes, reset upload mode too:

```tsx
const handleOpenChange = (nextOpen: boolean) => {
  if (!nextOpen) {
    setIsUploading(false);
    resetUploadForm();
  }

  onOpenChange(nextOpen);
};
```

Use that handler:

```tsx
<Dialog open={open} onOpenChange={handleOpenChange}>
```

## Fix header overlap

The Radix close button is always absolute on the top-right, while your header action is also on the right. Reserve space for it by adding `pr-16` to the header’s action row, and do not use a full-width layout that reaches the cross button. The current dialog close control is rendered at `top-4 right-4`.  

```tsx
<DialogHeader className="shrink-0 border-b px-6 pt-5 pb-3 pr-16">
  <div className="flex items-center justify-between gap-4">
    <div className="min-w-0">
      <DialogTitle className="flex items-center gap-2 text-lg">
        <Users className="h-5 w-5 shrink-0 text-primary" />
        <span className="truncate">
          {isUploading
            ? `Upload KYC — ${tenant.name}`
            : `Occupants — ${tenant.name}`}
        </span>
      </DialogTitle>
    </div>

    <Button
      type="button"
      variant="secondary"
      size="sm"
      className="mr-2 shrink-0"
      onClick={() => {
        setIsUploading((current) => !current);
        resetUploadForm();
      }}
    >
      {isUploading ? (
        <>
          <X className="mr-2 h-4 w-4" />
          Cancel Upload
        </>
      ) : (
        <>
          <Upload className="mr-2 h-4 w-4" />
          Upload KYC
        </>
      )}
    </Button>
  </div>
</DialogHeader>
```

The important parts are:

- `pr-16` creates permanent space for the Radix close cross.
- `mr-2` adds a small gap before that reserved space.
- `shrink-0` stops the button from compressing into the title.
- The title changes by mode, so the user clearly knows whether they are reviewing records or uploading KYC.

## Render one mode only

Replace the current structure that renders the upload form and then always renders the split viewer beneath it.

### Incorrect structure

```tsx
{isUploading && <KycUploadForm />}

<div className="flex flex-1 min-h-0">
  <OccupantsList />
  <OccupantPreview />
</div>
```

This is why the list and preview appear underneath the upload form.

### Correct structure

```tsx
<div className="min-h-0 flex-1 overflow-hidden">
  {isUploading ? (
    <div className="h-full overflow-y-auto bg-muted/20 px-6 py-5">
      <OccupantKycUploadForm
        tenantId={tenant.id}
        onCancel={() => {
          resetUploadForm();
          setIsUploading(false);
        }}
        onUploaded={async (newOccupant) => {
          await loadOccupants(tenant.id);

          if (newOccupant) {
            setSelectedOccupant(newOccupant);
          }

          resetUploadForm();
          setIsUploading(false);
        }}
      />
    </div>
  ) : (
    <div className="flex h-full min-h-0">
      <OccupantsList
        occupants={occupants}
        selectedOccupant={selectedOccupant}
        onSelect={handleSelectOccupant}
      />

      <OccupantDocumentPreview
        tenant={tenant}
        occupant={selectedOccupant}
        selectedDocument={selectedDocument}
        onSelectDocument={setSelectedDocument}
        onMarkInactive={handleMarkInactive}
        onDelete={handleDelete}
      />
    </div>
  )}
</div>
```

This guarantees:

- Clicking **Upload KYC** hides the occupant count/list.
- Clicking **Upload KYC** hides the document previewer.
- Clicking **Cancel Upload** returns to the original list + previewer layout.
- A successful upload reloads occupants and returns to viewer mode.

The currently rendered dialog has the upload form followed by a persistent `flex flex-1 min-h-0` split panel, confirming that the two views are not mutually exclusive yet.  

## Use a scrollable upload view

Your dialog has a fixed `h-[92vh]`, while the KYC form contains several required fields and file inputs. Keep the header fixed and make only the upload body scroll:

```tsx
{isUploading ? (
  <div className="h-full overflow-y-auto">
    <div className="mx-auto w-full max-w-3xl p-6">
      <OccupantKycUploadForm
        tenantId={tenant.id}
        onCancel={() => setIsUploading(false)}
        onUploaded={handleUploadSuccess}
      />
    </div>
  </div>
) : (
  // Viewer panes
)}
```

Do not use `flex-shrink-0` for the upload form wrapper. In the current markup, that wrapper can consume fixed vertical space before the list/viewer area, rather than allowing the upload form itself to scroll naturally.  

## Recommended full dialog shape

```tsx
<Dialog open={open} onOpenChange={handleOpenChange}>
  <DialogContent className="flex h-[92vh] max-w-[95vw] flex-col gap-0 overflow-hidden p-0 xl:max-w-[1400px]">
    <DialogHeader className="shrink-0 border-b px-6 pt-5 pb-3 pr-16">
      <div className="flex items-center justify-between gap-4">
        <div className="min-w-0">
          <DialogTitle className="flex items-center gap-2 text-lg">
            <Users className="h-5 w-5 shrink-0 text-primary" />
            <span className="truncate">
              {isUploading
                ? `Upload KYC — ${tenant.name}`
                : `Occupants — ${tenant.name}`}
            </span>
          </DialogTitle>
        </div>

        <Button
          type="button"
          variant="secondary"
          size="sm"
          className="mr-2 shrink-0"
          onClick={() => {
            setIsUploading((current) => !current);
            resetUploadForm();
          }}
        >
          {isUploading ? (
            <>
              <X className="mr-2 h-4 w-4" />
              Cancel Upload
            </>
          ) : (
            <>
              <Upload className="mr-2 h-4 w-4" />
              Upload KYC
            </>
          )}
        </Button>
      </div>
    </DialogHeader>

    <main className="min-h-0 flex-1 overflow-hidden">
      {isUploading ? (
        <div className="h-full overflow-y-auto bg-muted/20">
          <div className="mx-auto w-full max-w-3xl p-6">
            <OccupantKycUploadForm
              tenantId={tenant.id}
              onCancel={() => {
                resetUploadForm();
                setIsUploading(false);
              }}
              onUploaded={handleUploadSuccess}
            />
          </div>
        </div>
      ) : (
        <div className="flex h-full min-h-0">
          <OccupantsList />
          <OccupantDocumentPreview />
        </div>
      )}
    </main>
  </DialogContent>
</Dialog>
```

## Upload success handler

Use this so the latest occupant appears immediately after the upload:

```tsx
const handleUploadSuccess = async (occupant?: Occupant) => {
  if (!tenant?.id) return;

  const refreshedOccupants = await api.getOccupants(tenant.id);
  setOccupants(refreshedOccupants ?? []);

  const uploadedUuid = occupant?.occupantUuid ?? occupant?.["Occupant UUID"];

  const uploadedOccupant =
    refreshedOccupants.find(
      (item) =>
        (item.occupantUuid ?? item["Occupant UUID"]) === uploadedUuid,
    ) ?? refreshedOccupants[0] ?? null;

  setSelectedOccupant(uploadedOccupant);
  setSelectedDocument(firstDocument(uploadedOccupant));
  resetUploadForm();
  setIsUploading(false);

  toast.success("Occupant KYC uploaded successfully");
};
```

The existing occupant records support both `occupantUuid` and legacy `"Occupant UUID"` compatibility mapping, so normalize either key when selecting the newly uploaded record.  