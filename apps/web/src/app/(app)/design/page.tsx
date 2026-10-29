import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Check, Download, Inbox, Upload } from "lucide-react";

import { ToastButton } from "./toast-button";
import { EmptyState } from "@/components/ledger/empty-state";
import { PageHeader } from "@/components/ledger/page-header";
import { Stamp } from "@/components/ledger/stamp";
import { StatTile } from "@/components/ledger/stat-tile";
import {
  DocumentStatusStamp,
  MatchStamp,
  ReviewStamp,
} from "@/components/ledger/status-stamps";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";

export const metadata: Metadata = { title: "Design system" };

const COLOURS = [
  { name: "Paper", token: "bg-background" },
  { name: "Card", token: "bg-card" },
  { name: "Ink", token: "bg-foreground" },
  { name: "Muted", token: "bg-muted" },
  { name: "Forest", token: "bg-primary" },
  { name: "Success", token: "bg-success" },
  { name: "Ochre", token: "bg-warning" },
  { name: "Brick", token: "bg-destructive" },
];

const LINES = [
  { sku: "NW-1042", item: "Chai tea, 10 boxes × 20 bags", qty: 12, price: "18.00", total: "216.00" },
  { sku: "NW-2210", item: "Aniseed syrup, 12 × 550 ml", qty: 6, price: "10.00", total: "60.00" },
  { sku: "NW-3307", item: "Chef Anton's Cajun seasoning", qty: 4, price: "22.00", total: "88.00" },
];

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="grid gap-4 md:grid-cols-[10rem_1fr] md:gap-8">
      <h2 className="eyebrow pt-1">{title}</h2>
      <div className="min-w-0">{children}</div>
    </section>
  );
}

/** Every Ledger component on one page, to review the whole look at once. */
export default function DesignPage() {
  return (
    <>
      <PageHeader
        eyebrow="Reference"
        title="Design system"
        description="The Ledger look: warm paper, ink and one forest-green accent. Every screen is built from these pieces."
      />

      <Section title="Colour">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
          {COLOURS.map((colour) => (
            <div key={colour.name} className="overflow-hidden rounded-lg border bg-card shadow-paper">
              <div className={`h-16 border-b ${colour.token}`} />
              <div className="px-3 py-2">
                <p className="text-sm font-medium">{colour.name}</p>
                <p className="font-mono text-xs text-muted-foreground">{colour.token}</p>
              </div>
            </div>
          ))}
        </div>
      </Section>

      <Section title="Type">
        <div className="space-y-4">
          <p className="font-heading text-[2.5rem] leading-tight font-medium tracking-[-0.02em]">
            Fraunces for titles
          </p>
          <p className="max-w-xl leading-relaxed">
            IBM Plex Sans for everything you read and click. Calm, clear and a little technical,
            which suits a finance tool.
          </p>
          <p className="numeric text-lg">INV-2026-0418 · 2026-04-03 · €12,480.50</p>
          <p className="eyebrow">Small-caps eyebrow label</p>
        </div>
      </Section>

      <Section title="Buttons">
        <div className="flex flex-wrap items-center gap-3">
          <Button>
            <Check /> Approve
          </Button>
          <Button variant="outline">
            <Download /> Export
          </Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
          <Button variant="destructive">Reject</Button>
          <Button variant="link">Link</Button>
          <Button size="sm">Small</Button>
          <Button size="lg">Large</Button>
          <Button disabled>Disabled</Button>
        </div>
      </Section>

      <Section title="Stamps">
        <div className="space-y-3">
          <div className="flex flex-wrap gap-2">
            <Stamp>Neutral</Stamp>
            <Stamp tone="accent">Accent</Stamp>
            <Stamp tone="success">Success</Stamp>
            <Stamp tone="warning">Warning</Stamp>
            <Stamp tone="danger">Danger</Stamp>
          </div>
          <div className="flex flex-wrap gap-2">
            <DocumentStatusStamp status="processing" />
            <DocumentStatusStamp status="processed" />
            <MatchStamp status="matched" />
            <MatchStamp status="needs_review" />
            <MatchStamp status="waiting" />
            <ReviewStamp status="approved" />
            <ReviewStamp status="rejected" />
          </div>
        </div>
      </Section>

      <Section title="Stat tiles">
        <div className="grid gap-3 sm:grid-cols-3">
          <StatTile label="Invoices this month" value="148" detail="32 more than last month" />
          <StatTile label="Matched on their own" value="91%" tone="success" detail="135 of 148" />
          <StatTile label="Waiting for review" value="9" tone="warning" detail="Oldest is 2 days old" />
        </div>
      </Section>

      <Section title="Table">
        <div className="rounded-lg border bg-card shadow-paper">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>SKU</TableHead>
                <TableHead>Item</TableHead>
                <TableHead className="text-right">Qty</TableHead>
                <TableHead className="text-right">Unit price</TableHead>
                <TableHead className="text-right">Total</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {LINES.map((line) => (
                <TableRow key={line.sku}>
                  <TableCell className="numeric text-muted-foreground">{line.sku}</TableCell>
                  <TableCell>{line.item}</TableCell>
                  <TableCell className="numeric text-right">{line.qty}</TableCell>
                  <TableCell className="numeric text-right">{line.price}</TableCell>
                  <TableCell className="numeric text-right">{line.total}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      </Section>

      <Section title="Forms">
        <div className="grid max-w-lg gap-3">
          <Input placeholder="Search vendor or invoice number" />
          <Textarea placeholder="Why are you rejecting this invoice?" />
        </div>
      </Section>

      <Section title="Card">
        <Card className="max-w-lg">
          <CardHeader>
            <p className="eyebrow">Invoice</p>
            <CardTitle>Exotic Liquids Ltd.</CardTitle>
            <CardDescription>INV-2026-0418 · due 3 May 2026</CardDescription>
          </CardHeader>
          <CardContent className="flex items-baseline justify-between">
            <span className="numeric text-2xl">€364.00</span>
            <MatchStamp status="needs_review" />
          </CardContent>
          <CardFooter className="justify-end gap-2">
            <Button variant="outline" size="sm">
              Reject
            </Button>
            <Button size="sm">Approve</Button>
          </CardFooter>
        </Card>
      </Section>

      <Section title="Empty state">
        <EmptyState
          icon={Inbox}
          title="Nothing waiting for review"
          description="Every invoice matched its order and receipt. New exceptions will appear here."
          action={
            <Button variant="outline">
              <Upload /> Upload documents
            </Button>
          }
        />
      </Section>

      <Section title="Toast">
        <ToastButton />
      </Section>
    </>
  );
}
