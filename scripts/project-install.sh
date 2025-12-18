#!/bin/bash

# =============================================================================
# Agent OS Project Installation Script
# Installs Agent OS into a project's codebase
# =============================================================================

set -e  # Exit on error

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
BASE_DIR="$HOME/pocket-agent-os"
PROJECT_DIR="$(pwd)"

# Source common functions
source "$SCRIPT_DIR/common-functions.sh"

# -----------------------------------------------------------------------------
# Default Values
# -----------------------------------------------------------------------------

DRY_RUN="false"
VERBOSE="false"
PROFILE=""
CLAUDE_CODE_COMMANDS=""
USE_CLAUDE_CODE_SUBAGENTS=""
AGENT_OS_COMMANDS=""
STANDARDS_AS_CLAUDE_CODE_SKILLS=""
RE_INSTALL="false"
OVERWRITE_ALL="false"
OVERWRITE_STANDARDS="false"
OVERWRITE_COMMANDS="false"
OVERWRITE_AGENTS="false"
INSTALLED_FILES=()

# -----------------------------------------------------------------------------
# Help Function
# -----------------------------------------------------------------------------

show_help() {
    cat << EOF
Usage: $0 [OPTIONS]

Install Agent OS into the current project directory.

Options:
    --profile PROFILE                        Use specified profile (default: from config.yml)
    --claude-code-commands [BOOL]            Install Claude Code commands (default: from config.yml)
    --use-claude-code-subagents [BOOL]       Use Claude Code subagents (default: from config.yml)
    --agent-os-commands [BOOL]               Install agent-os commands (default: from config.yml)
    --standards-as-claude-code-skills [BOOL] Use Claude Code Skills for standards (default: from config.yml)
    --re-install                             Delete and reinstall Agent OS
    --overwrite-all                          Overwrite all existing files during update
    --overwrite-standards                    Overwrite existing standards during update
    --overwrite-commands                     Overwrite existing commands during update
    --overwrite-agents                       Overwrite existing agents during update
    --dry-run                                Show what would be done without doing it
    --verbose                                Show detailed output
    -h, --help                               Show this help message

Note: Flags accept both hyphens and underscores (e.g., --use-claude-code-subagents or --use_claude_code_subagents)

Examples:
    $0
    $0 --profile rails
    $0 --claude-code-commands true --use-claude-code-subagents true
    $0 --agent-os-commands true --dry-run

EOF
    exit 0
}

# -----------------------------------------------------------------------------
# Parse Command Line Arguments
# -----------------------------------------------------------------------------

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        # Normalize flag by replacing underscores with hyphens
        local flag="${1//_/-}"

        case $flag in
            --profile)
                PROFILE="$2"
                shift 2
                ;;
            --claude-code-commands)
                read CLAUDE_CODE_COMMANDS shift_count <<< "$(parse_bool_flag "$CLAUDE_CODE_COMMANDS" "$2")"
                shift $shift_count
                ;;
            --use-claude-code-subagents)
                read USE_CLAUDE_CODE_SUBAGENTS shift_count <<< "$(parse_bool_flag "$USE_CLAUDE_CODE_SUBAGENTS" "$2")"
                shift $shift_count
                ;;
            --agent-os-commands)
                read AGENT_OS_COMMANDS shift_count <<< "$(parse_bool_flag "$AGENT_OS_COMMANDS" "$2")"
                shift $shift_count
                ;;
            --standards-as-claude-code-skills)
                read STANDARDS_AS_CLAUDE_CODE_SKILLS shift_count <<< "$(parse_bool_flag "$STANDARDS_AS_CLAUDE_CODE_SKILLS" "$2")"
                shift $shift_count
                ;;
            --re-install)
                RE_INSTALL="true"
                shift
                ;;
            --overwrite-all)
                OVERWRITE_ALL="true"
                shift
                ;;
            --overwrite-standards)
                OVERWRITE_STANDARDS="true"
                shift
                ;;
            --overwrite-commands)
                OVERWRITE_COMMANDS="true"
                shift
                ;;
            --overwrite-agents)
                OVERWRITE_AGENTS="true"
                shift
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --verbose)
                VERBOSE="true"
                shift
                ;;
            -h|--help)
                show_help
                ;;
            *)
                print_error "Unknown option: $1"
                show_help
                ;;
        esac
    done
}

# -----------------------------------------------------------------------------
# Configuration Functions
# -----------------------------------------------------------------------------

load_configuration() {
    # Load base configuration using common function
    load_base_config

    # Set effective values (command line overrides base config)
    EFFECTIVE_PROFILE="${PROFILE:-$BASE_PROFILE}"
    EFFECTIVE_CLAUDE_CODE_COMMANDS="${CLAUDE_CODE_COMMANDS:-$BASE_CLAUDE_CODE_COMMANDS}"
    EFFECTIVE_USE_CLAUDE_CODE_SUBAGENTS="${USE_CLAUDE_CODE_SUBAGENTS:-$BASE_USE_CLAUDE_CODE_SUBAGENTS}"
    EFFECTIVE_AGENT_OS_COMMANDS="${AGENT_OS_COMMANDS:-$BASE_AGENT_OS_COMMANDS}"
    EFFECTIVE_STANDARDS_AS_CLAUDE_CODE_SKILLS="${STANDARDS_AS_CLAUDE_CODE_SKILLS:-$BASE_STANDARDS_AS_CLAUDE_CODE_SKILLS}"
    EFFECTIVE_VERSION="$BASE_VERSION"

    # PocketFlow enhancement settings (v3.0)
    EFFECTIVE_SESSION_MANAGEMENT="${SESSION_MANAGEMENT:-$BASE_SESSION_MANAGEMENT}"
    EFFECTIVE_EXPERTISE_TRACKING="${EXPERTISE_TRACKING:-$BASE_EXPERTISE_TRACKING}"
    EFFECTIVE_PROGRESS_TRACKING="${PROGRESS_TRACKING:-$BASE_PROGRESS_TRACKING}"
    EFFECTIVE_SMART_ROUTING="${SMART_ROUTING:-$BASE_SMART_ROUTING}"
    EFFECTIVE_SELF_IMPROVEMENT="${SELF_IMPROVEMENT:-$BASE_SELF_IMPROVEMENT}"

    # Validate configuration using common function (may override EFFECTIVE_STANDARDS_AS_CLAUDE_CODE_SKILLS if dependency not met)
    validate_config "$EFFECTIVE_CLAUDE_CODE_COMMANDS" "$EFFECTIVE_USE_CLAUDE_CODE_SUBAGENTS" "$EFFECTIVE_AGENT_OS_COMMANDS" "$EFFECTIVE_STANDARDS_AS_CLAUDE_CODE_SKILLS" "$EFFECTIVE_PROFILE"

    print_verbose "Configuration loaded:"
    print_verbose "  Profile: $EFFECTIVE_PROFILE"
    print_verbose "  Claude Code commands: $EFFECTIVE_CLAUDE_CODE_COMMANDS"
    print_verbose "  Use Claude Code subagents: $EFFECTIVE_USE_CLAUDE_CODE_SUBAGENTS"
    print_verbose "  Agent OS commands: $EFFECTIVE_AGENT_OS_COMMANDS"
    print_verbose "  Standards as Claude Code Skills: $EFFECTIVE_STANDARDS_AS_CLAUDE_CODE_SKILLS"
    print_verbose "  Session Management: $EFFECTIVE_SESSION_MANAGEMENT"
    print_verbose "  Expertise Tracking: $EFFECTIVE_EXPERTISE_TRACKING"
    print_verbose "  Smart Routing: $EFFECTIVE_SMART_ROUTING"
}

# -----------------------------------------------------------------------------
# Installation Functions
# -----------------------------------------------------------------------------

# Install standards files
install_standards() {
    if [[ "$DRY_RUN" != "true" ]]; then
        print_status "Installing standards"
    fi

    local standards_count=0

    while read file; do
        if [[ "$file" == standards/* ]]; then
            local source=$(get_profile_file "$EFFECTIVE_PROFILE" "$file" "$BASE_DIR")
            local dest="$PROJECT_DIR/agent-os/$file"

            if [[ -f "$source" ]]; then
                local installed_file=$(copy_file "$source" "$dest")
                if [[ -n "$installed_file" ]]; then
                    INSTALLED_FILES+=("$installed_file")
                    ((standards_count++)) || true
                fi
            fi
        fi
    done < <(get_profile_files "$EFFECTIVE_PROFILE" "$BASE_DIR" "standards")

    if [[ "$DRY_RUN" != "true" ]]; then
        if [[ $standards_count -gt 0 ]]; then
            echo "✓ Installed $standards_count standards in agent-os/standards"
        fi
    fi
}

# Install and compile single-agent mode commands
# Install Claude Code commands with delegation (multi-agent files)
install_claude_code_commands_with_delegation() {
    if [[ "$DRY_RUN" != "true" ]]; then
        print_status "Installing Claude Code commands (with delegation to subagents)..."
    fi

    local commands_count=0
    local target_dir="$PROJECT_DIR/.claude/commands/agent-os"

    mkdir -p "$target_dir"

    while read file; do
        # Process multi-agent command files OR orchestrate-tasks special case
        if [[ "$file" == commands/*/multi-agent/* ]] || [[ "$file" == commands/orchestrate-tasks/orchestrate-tasks.md ]]; then
            local source=$(get_profile_file "$EFFECTIVE_PROFILE" "$file" "$BASE_DIR")
            if [[ -f "$source" ]]; then
                # Extract command name from path (e.g., commands/create-spec/multi-agent/create-spec.md -> create-spec)
                local cmd_name=$(echo "$file" | cut -d'/' -f2)
                local dest="$target_dir/${cmd_name}.md"

                # Compile with workflow and standards injection (includes conditional compilation)
                local compiled=$(compile_command "$source" "$dest" "$BASE_DIR" "$EFFECTIVE_PROFILE")
                if [[ "$DRY_RUN" == "true" ]]; then
                    INSTALLED_FILES+=("$dest")
                fi
                ((commands_count++)) || true
            fi
        fi
    done < <(get_profile_files "$EFFECTIVE_PROFILE" "$BASE_DIR" "commands")

    if [[ "$DRY_RUN" != "true" ]]; then
        if [[ $commands_count -gt 0 ]]; then
            echo "✓ Installed $commands_count Claude Code commands (with delegation)"
        fi
    fi
}

# Install Claude Code commands without delegation (single-agent files with injection)
install_claude_code_commands_without_delegation() {
    if [[ "$DRY_RUN" != "true" ]]; then
        print_status "Installing Claude Code commands (without delegation)..."
    fi

    local commands_count=0

    while read file; do
        # Process single-agent command files OR orchestrate-tasks special case
        if [[ "$file" == commands/*/single-agent/* ]] || [[ "$file" == commands/orchestrate-tasks/orchestrate-tasks.md ]]; then
            local source=$(get_profile_file "$EFFECTIVE_PROFILE" "$file" "$BASE_DIR")
            if [[ -f "$source" ]]; then
                # Handle orchestrate-tasks specially (flat destination)
                if [[ "$file" == commands/orchestrate-tasks/orchestrate-tasks.md ]]; then
                    local dest="$PROJECT_DIR/.claude/commands/agent-os/orchestrate-tasks.md"
                    # Compile without PHASE embedding for orchestrate-tasks
                    local compiled=$(compile_command "$source" "$dest" "$BASE_DIR" "$EFFECTIVE_PROFILE" "")
                    if [[ "$DRY_RUN" == "true" ]]; then
                        INSTALLED_FILES+=("$dest")
                    fi
                    ((commands_count++)) || true
                else
                    # Only install non-numbered files (e.g., plan-product.md, not 1-product-concept.md)
                    local filename=$(basename "$file")
                    if [[ ! "$filename" =~ ^[0-9]+-.*\.md$ ]]; then
                        # Extract command name (e.g., commands/plan-product/single-agent/plan-product.md -> plan-product.md)
                        local cmd_name=$(echo "$file" | sed 's|commands/\([^/]*\)/single-agent/.*|\1|')
                        local dest="$PROJECT_DIR/.claude/commands/agent-os/$cmd_name.md"

                        # Compile with PHASE embedding (mode="embed")
                        local compiled=$(compile_command "$source" "$dest" "$BASE_DIR" "$EFFECTIVE_PROFILE" "embed")
                        if [[ "$DRY_RUN" == "true" ]]; then
                            INSTALLED_FILES+=("$dest")
                        fi
                        ((commands_count++)) || true
                    fi
                fi
            fi
        fi
    done < <(get_profile_files "$EFFECTIVE_PROFILE" "$BASE_DIR" "commands")

    if [[ "$DRY_RUN" != "true" ]]; then
        if [[ $commands_count -gt 0 ]]; then
            echo "✓ Installed $commands_count Claude Code commands (without delegation)"
        fi
    fi
}

# Install Claude Code static agents
install_claude_code_agents() {
    if [[ "$DRY_RUN" != "true" ]]; then
        print_status "Installing Claude Code agents..."
    fi

    local agents_count=0
    local target_dir="$PROJECT_DIR/.claude/agents/agent-os"
    
    mkdir -p "$target_dir"

    while read file; do
        # Include all agent files (flatten structure - no subfolders in output)
        if [[ "$file" == agents/*.md ]] && [[ "$file" != agents/templates/* ]]; then
            local source=$(get_profile_file "$EFFECTIVE_PROFILE" "$file" "$BASE_DIR")
            if [[ -f "$source" ]]; then
                # Get just the filename (flatten directory structure)
                local filename=$(basename "$file")
                local dest="$target_dir/$filename"
                
                # Compile with workflow and standards injection
                local compiled=$(compile_agent "$source" "$dest" "$BASE_DIR" "$EFFECTIVE_PROFILE" "")
                if [[ "$DRY_RUN" == "true" ]]; then
                    INSTALLED_FILES+=("$dest")
                fi
                ((agents_count++)) || true
            fi
        fi
    done < <(get_profile_files "$EFFECTIVE_PROFILE" "$BASE_DIR" "agents")

    if [[ "$DRY_RUN" != "true" ]]; then
        if [[ $agents_count -gt 0 ]]; then
            echo "✓ Installed $agents_count Claude Code agents"
        fi
    fi
}

# Install agent-os commands (single-agent files with injection)
install_agent_os_commands() {
    if [[ "$DRY_RUN" != "true" ]]; then
        print_status "Installing agent-os commands..."
    fi

    local commands_count=0

    while read file; do
        # Process single-agent command files OR orchestrate-tasks special case
        if [[ "$file" == commands/*/single-agent/* ]] || [[ "$file" == commands/orchestrate-tasks/orchestrate-tasks.md ]]; then
            local source=$(get_profile_file "$EFFECTIVE_PROFILE" "$file" "$BASE_DIR")
            if [[ -f "$source" ]]; then
                # Handle orchestrate-tasks specially (preserve folder structure)
                if [[ "$file" == commands/orchestrate-tasks/orchestrate-tasks.md ]]; then
                    local dest="$PROJECT_DIR/agent-os/commands/orchestrate-tasks/orchestrate-tasks.md"
                else
                    # Extract command name and preserve numbering
                    local cmd_path=$(echo "$file" | sed 's|commands/\([^/]*\)/single-agent/\(.*\)|\1/\2|')
                    local dest="$PROJECT_DIR/agent-os/commands/$cmd_path"
                fi

                # Compile with workflow and standards injection and PHASE embedding
                local compiled=$(compile_command "$source" "$dest" "$BASE_DIR" "$EFFECTIVE_PROFILE" "embed")
                if [[ "$DRY_RUN" == "true" ]]; then
                    INSTALLED_FILES+=("$dest")
                fi
                ((commands_count++)) || true
            fi
        fi
    done < <(get_profile_files "$EFFECTIVE_PROFILE" "$BASE_DIR" "commands")

    if [[ "$DRY_RUN" != "true" ]]; then
        if [[ $commands_count -gt 0 ]]; then
            echo "✓ Installed $commands_count agent-os commands"
        fi
    fi
}

# Create agent-os folder structure
create_agent_os_folder() {
    if [[ "$DRY_RUN" != "true" ]]; then
        print_status "Installing agent-os folder"
    fi

    # Create the main agent-os folder
    ensure_dir "$PROJECT_DIR/agent-os"

    # Create the configuration file
    local config_file=$(write_project_config "$EFFECTIVE_VERSION" "$EFFECTIVE_PROFILE" \
        "$EFFECTIVE_CLAUDE_CODE_COMMANDS" "$EFFECTIVE_USE_CLAUDE_CODE_SUBAGENTS" \
        "$EFFECTIVE_AGENT_OS_COMMANDS" "$EFFECTIVE_STANDARDS_AS_CLAUDE_CODE_SKILLS")
    if [[ "$DRY_RUN" == "true" && -n "$config_file" ]]; then
        INSTALLED_FILES+=("$config_file")
    fi

    if [[ "$DRY_RUN" != "true" ]]; then
        echo "✓ Created agent-os folder"
        echo "✓ Created agent-os project configuration"
    fi
}

# Install expertise directory and templates (PocketFlow v3.0)
install_expertise_templates() {
    if [[ "$EFFECTIVE_EXPERTISE_TRACKING" != "true" ]]; then
        return
    fi

    if [[ "$DRY_RUN" != "true" ]]; then
        print_status "Installing expertise templates..."
    fi

    local expertise_dir="$PROJECT_DIR/agent-os/expertise"
    ensure_dir "$expertise_dir"

    # Copy index template
    local index_template=$(get_profile_file "$EFFECTIVE_PROFILE" "expertise/_index.yaml.template" "$BASE_DIR")
    if [[ -f "$index_template" ]]; then
        local dest="$expertise_dir/_index.yaml"
        local installed_file=$(copy_file "$index_template" "$dest")
        if [[ "$DRY_RUN" == "true" && -n "$installed_file" ]]; then
            INSTALLED_FILES+=("$installed_file")
        fi
    fi

    # Copy expertise templates to _templates subfolder
    local templates_dir="$expertise_dir/_templates"
    ensure_dir "$templates_dir"

    while read file; do
        if [[ "$file" == expertise/_templates/*.yaml.template ]]; then
            local source=$(get_profile_file "$EFFECTIVE_PROFILE" "$file" "$BASE_DIR")
            if [[ -f "$source" ]]; then
                local filename=$(basename "$file")
                local dest="$templates_dir/$filename"
                local installed_file=$(copy_file "$source" "$dest")
                if [[ "$DRY_RUN" == "true" && -n "$installed_file" ]]; then
                    INSTALLED_FILES+=("$installed_file")
                fi
            fi
        fi
    done < <(get_profile_files "$EFFECTIVE_PROFILE" "$BASE_DIR" "expertise")

    if [[ "$DRY_RUN" != "true" ]]; then
        echo "✓ Created expertise directory with templates"
    fi
}

# Install sessions directory (PocketFlow v3.0)
install_sessions_directory() {
    if [[ "$EFFECTIVE_SESSION_MANAGEMENT" != "true" ]]; then
        return
    fi

    local sessions_dir="$PROJECT_DIR/agent-os/sessions"
    ensure_dir "$sessions_dir"

    # Create .gitkeep to ensure directory is tracked
    if [[ "$DRY_RUN" != "true" ]]; then
        touch "$sessions_dir/.gitkeep"
        echo "✓ Created sessions directory"
    fi
}

# Install routing configuration template (PocketFlow v3.0)
install_routing_template() {
    if [[ "$EFFECTIVE_SMART_ROUTING" != "true" ]]; then
        return
    fi

    local routing_template=$(get_profile_file "$EFFECTIVE_PROFILE" "routing/routing.yaml.template" "$BASE_DIR")
    if [[ -f "$routing_template" ]]; then
        local dest="$PROJECT_DIR/agent-os/routing.yaml.example"
        local installed_file=$(copy_file "$routing_template" "$dest")
        if [[ "$DRY_RUN" == "true" && -n "$installed_file" ]]; then
            INSTALLED_FILES+=("$installed_file")
        fi
        if [[ "$DRY_RUN" != "true" ]]; then
            echo "✓ Created routing configuration template (routing.yaml.example)"
        fi
    fi
}

# Install PocketFlow CLI wrapper script (PocketFlow v3.0)
# Creates a convenience script to run Python flows from within the project
install_pocketflow_wrapper() {
    # Only install if session management is enabled (indicates PocketFlow features are wanted)
    if [[ "$EFFECTIVE_SESSION_MANAGEMENT" != "true" ]]; then
        return
    fi

    # Check if Python framework exists in base installation
    if [[ ! -f "$BASE_DIR/scripts/run-flow.py" ]]; then
        print_verbose "PocketFlow CLI not found in base installation, skipping wrapper"
        return
    fi

    local wrapper_script="$PROJECT_DIR/agent-os/run-flow"

    if [[ "$DRY_RUN" == "true" ]]; then
        INSTALLED_FILES+=("$wrapper_script")
        return
    fi

    # Create the wrapper script
    cat > "$wrapper_script" << 'WRAPPER_EOF'
#!/bin/bash
# Agent OS PocketFlow CLI Wrapper
# Runs Python flows from the base Agent OS installation
#
# Usage:
#   ./agent-os/run-flow status
#   ./agent-os/run-flow implement --spec my-feature
#   ./agent-os/run-flow bootstrap
#
# This wrapper automatically:
#   - Detects the project root (where this script lives)
#   - Calls the base installation's run-flow.py
#   - Passes --project automatically

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
BASE_INSTALL="$HOME/pocket-agent-os"
RUNNER="$BASE_INSTALL/scripts/run-flow.py"

# Check if runner exists
if [[ ! -f "$RUNNER" ]]; then
    echo "Error: PocketFlow runner not found at $RUNNER"
    echo "Make sure Pocket Agent OS base installation exists at ~/pocket-agent-os"
    exit 1
fi

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is required but not found"
    exit 1
fi

# If no arguments, show help
if [[ $# -eq 0 ]]; then
    python3 "$RUNNER" --help
    exit 0
fi

# Get the command (first argument)
COMMAND="$1"
shift

# For commands that need --project, inject it automatically if not provided
case "$COMMAND" in
    status|bootstrap|implement|spec)
        # Check if --project or -p is already in args
        if [[ ! " $* " =~ " --project " ]] && [[ ! " $* " =~ " -p " ]]; then
            python3 "$RUNNER" "$COMMAND" --project "$PROJECT_ROOT" "$@"
        else
            python3 "$RUNNER" "$COMMAND" "$@"
        fi
        ;;
    *)
        # Pass through as-is
        python3 "$RUNNER" "$COMMAND" "$@"
        ;;
esac
WRAPPER_EOF

    # Make it executable
    chmod +x "$wrapper_script"

    echo "✓ Created PocketFlow CLI wrapper (run-flow)"
}

# Perform fresh installation
perform_installation() {
    # Show dry run warning at the top if applicable
    if [[ "$DRY_RUN" == "true" ]]; then
        print_warning "DRY RUN - No files will be actually created"
        echo ""
    fi

    # Display configuration at the top
    echo ""
    print_status "Configuration:"
    echo -e "  Profile: ${YELLOW}$EFFECTIVE_PROFILE${NC}"
    echo -e "  Claude Code commands: ${YELLOW}$EFFECTIVE_CLAUDE_CODE_COMMANDS${NC}"
    echo -e "  Use Claude Code subagents: ${YELLOW}$EFFECTIVE_USE_CLAUDE_CODE_SUBAGENTS${NC}"
    echo -e "  Standards as Claude Code Skills: ${YELLOW}$EFFECTIVE_STANDARDS_AS_CLAUDE_CODE_SKILLS${NC}"
    echo -e "  Agent OS commands: ${YELLOW}$EFFECTIVE_AGENT_OS_COMMANDS${NC}"
    echo -e "  Session Management: ${YELLOW}$EFFECTIVE_SESSION_MANAGEMENT${NC}"
    echo -e "  Expertise Tracking: ${YELLOW}$EFFECTIVE_EXPERTISE_TRACKING${NC}"
    echo -e "  Smart Routing: ${YELLOW}$EFFECTIVE_SMART_ROUTING${NC}"
    echo ""

    # In dry run mode, just collect files silently
    if [[ "$DRY_RUN" == "true" ]]; then
        # Collect files without output
        create_agent_os_folder
        install_standards
        install_expertise_templates
        install_sessions_directory
        install_routing_template
        install_pocketflow_wrapper

        # Install Claude Code files if enabled
        if [[ "$EFFECTIVE_CLAUDE_CODE_COMMANDS" == "true" ]]; then
            if [[ "$EFFECTIVE_USE_CLAUDE_CODE_SUBAGENTS" == "true" ]]; then
                install_claude_code_commands_with_delegation
                install_claude_code_agents
            else
                install_claude_code_commands_without_delegation
            fi
            install_claude_code_skills
            install_improve_skills_command
        fi

        # Install agent-os commands if enabled
        if [[ "$EFFECTIVE_AGENT_OS_COMMANDS" == "true" ]]; then
            install_agent_os_commands
        fi

        echo ""
        print_status "The following files would be created:"
        for file in "${INSTALLED_FILES[@]}"; do
            # Make paths relative to project root
            local relative_path="${file#$PROJECT_DIR/}"
            echo "  - $relative_path"
        done
    else
        # Normal installation with output
        create_agent_os_folder
        echo ""

        install_standards
        echo ""

        # Install PocketFlow enhancement directories (v3.0)
        install_expertise_templates
        install_sessions_directory
        install_routing_template
        install_pocketflow_wrapper
        echo ""

        # Install Claude Code files if enabled
        if [[ "$EFFECTIVE_CLAUDE_CODE_COMMANDS" == "true" ]]; then
            if [[ "$EFFECTIVE_USE_CLAUDE_CODE_SUBAGENTS" == "true" ]]; then
                install_claude_code_commands_with_delegation
                echo ""
                install_claude_code_agents
                echo ""
            else
                install_claude_code_commands_without_delegation
                echo ""
            fi
            install_claude_code_skills
            install_improve_skills_command
            echo ""
        fi

        # Install agent-os commands if enabled
        if [[ "$EFFECTIVE_AGENT_OS_COMMANDS" == "true" ]]; then
            install_agent_os_commands
            echo ""
        fi
    fi

    if [[ "$DRY_RUN" == "true" ]]; then
        echo ""
        read -p "Proceed with actual installation? (y/n): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            DRY_RUN="false"
            INSTALLED_FILES=()
            perform_installation
        fi
    else
        print_success "Agent OS has been successfully installed in your project!"
        echo ""
        echo -e "${GREEN}Visit the docs for guides on how to use Agent OS: https://buildermethods.com/agent-os${NC}"
        echo ""
    fi
}

# Handle re-installation
handle_reinstallation() {
    print_section "Re-installation"

    print_warning "This will DELETE your current agent-os/ folder and reinstall from scratch."
    echo ""

    # Check for Claude Code files
    if [[ -d "$PROJECT_DIR/.claude/agents/agent-os" ]] || [[ -d "$PROJECT_DIR/.claude/commands/agent-os" ]]; then
        print_warning "This will also DELETE:"
        [[ -d "$PROJECT_DIR/.claude/agents/agent-os" ]] && echo "  - .claude/agents/agent-os/"
        [[ -d "$PROJECT_DIR/.claude/commands/agent-os" ]] && echo "  - .claude/commands/agent-os/"
        echo ""
    fi

    read -p "Are you sure you want to proceed? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_status "Re-installation cancelled"
        exit 0
    fi

    if [[ "$DRY_RUN" != "true" ]]; then
        print_status "Removing existing installation..."
        rm -rf "$PROJECT_DIR/agent-os"
        rm -rf "$PROJECT_DIR/.claude/agents/agent-os"
        rm -rf "$PROJECT_DIR/.claude/commands/agent-os"
        echo "✓ Existing installation removed"
        echo ""
    fi

    perform_installation
}

# -----------------------------------------------------------------------------
# Main Execution
# -----------------------------------------------------------------------------

main() {
    print_section "Agent OS Project Installation"

    # Parse command line arguments
    parse_arguments "$@"

    # Check if we're trying to install in the base installation directory
    check_not_base_installation

    # Validate base installation using common function
    validate_base_installation

    # Load configuration
    load_configuration

    # Check if Agent OS is already installed
    if is_agent_os_installed "$PROJECT_DIR"; then
        if [[ "$RE_INSTALL" == "true" ]]; then
            handle_reinstallation
        else
            # Delegate to update script
            print_status "Agent OS is already installed. Running update..."
            exec "$BASE_DIR/scripts/project-update.sh" "$@"
        fi
    else
        # Fresh installation
        perform_installation
    fi
}

# Run main function
main "$@"
