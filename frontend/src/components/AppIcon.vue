<script setup>
import { computed } from "vue";
import {
  Activity,
  ArrowRight,
  ArrowUp,
  ChevronDown,
  ChevronUp,
  Circle,
  ClipboardCheck,
  ListChecks,
  LoaderCircle,
  Menu,
  MessageSquareText,
  PanelRight,
  Pin,
  Play,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
  Users,
  Wrench,
  X,
} from "@lucide/vue";

const props = defineProps({
  name: {
    type: String,
    required: true,
  },
});

const icons = {
  Activity,
  ArrowRight,
  ArrowUp,
  ChevronDown,
  ChevronUp,
  Circle,
  ClipboardCheck,
  ListChecks,
  LoaderCircle,
  Menu,
  MessageSquareText,
  PanelRight,
  Pin,
  Play,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
  Users,
  Wrench,
  X,
};

const icon = computed(() => icons[props.name] || Circle);
</script>

<template>
  <component :is="icon" class="lucide" aria-hidden="true" />
</template>
