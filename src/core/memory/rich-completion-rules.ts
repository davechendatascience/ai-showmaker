/**
 * Rich Completion Rules System
 * 
 * Provides evidence-based completion validation for different task types.
 * Uses rich context and evidence to determine when tasks are truly complete.
 */

import { 
  RichTaskContext, 
  TaskType, 
  EvidenceType, 
  ICompletionRules,
  Evidence,
  FileReference
} from './rich-memory-types';

export class RichCompletionRules implements ICompletionRules {
  
  checkCompletion(context: RichTaskContext): boolean {
    switch (context.taskType) {
      case 'simple_question':
        return this.checkSimpleQuestionCompletion(context);
      case 'coding_task':
        return this.checkCodingTaskCompletion(context);
      case 'research_task':
        return this.checkResearchTaskCompletion(context);
      case 'general_task':
        return this.checkGeneralTaskCompletion(context);
      default:
        return false;
    }
  }

  getRequiredEvidence(taskType: TaskType): EvidenceType[] {
    switch (taskType) {
      case 'simple_question':
        return ['file_creation', 'synthesis'];
      case 'coding_task':
        return ['file_creation', 'code_implementation', 'documentation'];
      case 'research_task':
        return ['file_creation', 'synthesis', 'documentation'];
      case 'general_task':
        return ['file_creation', 'execution'];
      default:
        return ['file_creation'];
    }
  }

  getCompletionCriteria(taskType: TaskType): string[] {
    switch (taskType) {
      case 'simple_question':
        return [
          'Answer file created with correct content',
          'Answer is directly provided to the question',
          'Evidence of synthesis or direct response'
        ];
      case 'coding_task':
        return [
          'Code file created with working implementation',
          'Code contains actual functions/classes (not just comments)',
          'Code is properly documented or has inline documentation',
          'Code file has sufficient complexity to solve the problem'
        ];
      case 'research_task':
        return [
          'Summary or research document created',
          'Document contains synthesized findings',
          'Document has proper structure and organization',
          'Evidence of information gathering and analysis'
        ];
      case 'general_task':
        return [
          'Task output file created',
          'Output contains relevant content',
          'Evidence of successful execution'
        ];
      default:
        return ['Output file created'];
    }
  }

  private checkSimpleQuestionCompletion(context: RichTaskContext): boolean {
    // Simple question requires answer with evidence
    const hasAnswerFile = this.hasEvidenceType(context, 'file_creation');
    const hasSynthesis = this.hasEvidenceType(context, 'synthesis');
    const hasDirectAnswer = this.hasDirectAnswer(context);
    
    // Check if answer file contains actual answer (not just placeholder)
    const answerFiles = context.files.filter(f => 
      f.fileType === 'documentation' && 
      (f.filePath.includes('answer') || f.filePath.includes('response'))
    );
    
    const hasValidAnswer = answerFiles.some(file => 
      file.content.length > 20 && 
      !file.content.includes('placeholder') &&
      !file.content.includes('TODO')
    );
    
    return hasAnswerFile && (hasSynthesis || hasDirectAnswer) && hasValidAnswer;
  }

  private checkCodingTaskCompletion(context: RichTaskContext): boolean {
    // Coding task requires code file with documentation
    const hasCodeFile = this.hasEvidenceType(context, 'file_creation');
    const hasCodeImplementation = this.hasEvidenceType(context, 'code_implementation');
    const hasDocumentation = this.hasEvidenceType(context, 'documentation');
    
    // Check for actual code files (not just documentation)
    const codeFiles = context.files.filter(f => f.fileType === 'code');
    const hasActualCode = codeFiles.some(file => 
      this.isValidCodeFile(file) && 
      this.hasWorkingCode(file)
    );
    
    // Check for proper documentation
    const hasProperDocumentation = this.hasProperCodeDocumentation(context);
    
    // Check for sufficient code complexity
    const hasSufficientComplexity = this.hasSufficientCodeComplexity(context);
    
    return hasCodeFile && 
           hasCodeImplementation && 
           hasActualCode && 
           (hasDocumentation || hasProperDocumentation) &&
           hasSufficientComplexity;
  }

  private checkResearchTaskCompletion(context: RichTaskContext): boolean {
    // Research task requires summary with sources
    const hasSummaryFile = this.hasEvidenceType(context, 'file_creation');
    const hasSynthesis = this.hasEvidenceType(context, 'synthesis');
    const hasDocumentation = this.hasEvidenceType(context, 'documentation');
    
    // Check for research document
    const researchFiles = context.files.filter(f => 
      f.fileType === 'documentation' && 
      (f.filePath.includes('research') || 
       f.filePath.includes('summary') || 
       f.filePath.includes('analysis'))
    );
    
    const hasValidResearch = researchFiles.some(file => 
      file.content.length > 100 && 
      this.hasResearchStructure(file)
    );
    
    // Check for evidence of information gathering
    const hasInformationGathering = this.hasInformationGatheringEvidence(context);
    
    return hasSummaryFile && 
           (hasSynthesis || hasDocumentation) && 
           hasValidResearch &&
           hasInformationGathering;
  }

  private checkGeneralTaskCompletion(context: RichTaskContext): boolean {
    // General task requires result with evidence
    const hasResultFile = this.hasEvidenceType(context, 'file_creation');
    const hasExecution = this.hasEvidenceType(context, 'execution');
    const hasValidOutput = this.hasValidTaskOutput(context);
    
    return hasResultFile && hasExecution && hasValidOutput;
  }

  // Helper methods for evidence checking
  private hasEvidenceType(context: RichTaskContext, evidenceType: EvidenceType): boolean {
    return context.evidence.some(e => e.evidenceType === evidenceType);
  }

  private hasDirectAnswer(context: RichTaskContext): boolean {
    // Check if any action directly provided an answer
    return context.actions.some(action => 
      action.actionType === 'write_file' && 
      action.outputs.success &&
      action.outputs.result.includes('answer') &&
      action.outputs.result.length > 10
    );
  }

  private isValidCodeFile(file: FileReference): boolean {
    // Check if file is actually a code file
    const codeExtensions = ['.py', '.js', '.ts', '.java', '.cpp', '.go', '.rs'];
    const hasCodeExtension = codeExtensions.some(ext => file.filePath.endsWith(ext));
    const hasCodeContent = file.metadata?.language && file.metadata.language !== 'other';
    
    return hasCodeExtension || (hasCodeContent || false);
  }

  private hasWorkingCode(file: FileReference): boolean {
    // Check if file contains actual working code (not just comments)
    const content = file.content;
    
    // Remove comments and empty lines
    const codeLines = content.split('\n')
      .map(line => line.trim())
      .filter(line => 
        line.length > 0 && 
        !line.startsWith('#') && 
        !line.startsWith('//') && 
        !line.startsWith('/*') &&
        !line.startsWith('*')
      );
    
    // Check for actual code constructs
    const hasCodeConstructs = codeLines.some(line => 
      line.includes('def ') || 
      line.includes('function ') || 
      line.includes('class ') ||
      line.includes('const ') ||
      line.includes('let ') ||
      line.includes('var ') ||
      line.includes('public ') ||
      line.includes('private ')
    );
    
    // Check for sufficient code length
    const hasSufficientLength = codeLines.length >= 3;
    
    return hasCodeConstructs && hasSufficientLength;
  }

  private hasProperCodeDocumentation(context: RichTaskContext): boolean {
    // Check if code files have proper documentation
    const codeFiles = context.files.filter(f => f.fileType === 'code');
    
    return codeFiles.some(file => {
      const hasInlineDocs = file.metadata?.documentation && 
                           file.metadata.documentation.length > 50;
      const hasFunctionDocs = file.metadata?.functions && 
                             file.metadata.functions.length > 0;
      const hasClassDocs = file.metadata?.classes && 
                          file.metadata.classes.length > 0;
      
      return hasInlineDocs || hasFunctionDocs || hasClassDocs;
    });
  }

  private hasSufficientCodeComplexity(context: RichTaskContext): boolean {
    // Check if code has sufficient complexity to solve the problem
    const codeFiles = context.files.filter(f => f.fileType === 'code');
    
    return codeFiles.some(file => {
      const complexity = file.metadata?.complexity || 0;
      const functionCount = file.metadata?.functions?.length || 0;
      const classCount = file.metadata?.classes?.length || 0;
      
      // Require either complexity > 1, or multiple functions/classes
      return complexity > 1 || functionCount > 0 || classCount > 0;
    });
  }

  private hasResearchStructure(file: FileReference): boolean {
    // Check if research file has proper structure
    const content = file.content.toLowerCase();
    
    const hasStructure = 
      content.includes('#') || // Has headers
      content.includes('##') || // Has subheaders
      content.includes('summary') ||
      content.includes('conclusion') ||
      content.includes('findings');
    
    const hasContent = file.content.length > 200;
    
    return hasStructure && hasContent;
  }

  private hasInformationGatheringEvidence(context: RichTaskContext): boolean {
    // Check for evidence of information gathering
    const hasWebSearch = context.actions.some(action => 
      action.actionType === 'search_web' || 
      action.actionType === 'web_search'
    );
    
    const hasFileRead = context.actions.some(action => 
      action.actionType === 'read_file'
    );
    
    const hasSynthesis = this.hasEvidenceType(context, 'synthesis');
    
    return hasWebSearch || hasFileRead || hasSynthesis;
  }

  private hasValidTaskOutput(context: RichTaskContext): boolean {
    // Check if task has valid output
    const outputFiles = context.files.filter(f => 
      f.fileType === 'output' || 
      f.fileType === 'documentation'
    );
    
    return outputFiles.some(file => 
      file.content.length > 20 && 
      !file.content.includes('placeholder') &&
      !file.content.includes('TODO')
    );
  }

  // Detailed completion analysis
  getCompletionAnalysis(context: RichTaskContext): {
    isComplete: boolean;
    completionPercentage: number;
    missingRequirements: string[];
    completedRequirements: string[];
    evidence: Evidence[];
    recommendations: string[];
  } {
    const requiredEvidence = this.getRequiredEvidence(context.taskType);
    const criteria = this.getCompletionCriteria(context.taskType);
    
    const completedRequirements: string[] = [];
    const missingRequirements: string[] = [];
    const recommendations: string[] = [];
    
    // Check each requirement
    criteria.forEach(criterion => {
      if (this.checkCriterion(context, criterion)) {
        completedRequirements.push(criterion);
      } else {
        missingRequirements.push(criterion);
      }
    });
    
    // Check evidence
    const presentEvidence = requiredEvidence.filter(evidenceType => 
      this.hasEvidenceType(context, evidenceType)
    );
    
    const missingEvidence = requiredEvidence.filter(evidenceType => 
      !this.hasEvidenceType(context, evidenceType)
    );
    
    // Generate recommendations
    if (missingEvidence.length > 0) {
      recommendations.push(`Missing evidence types: ${missingEvidence.join(', ')}`);
    }
    
    if (missingRequirements.length > 0) {
      recommendations.push(`Missing requirements: ${missingRequirements.join(', ')}`);
    }
    
    // Calculate completion percentage
    const totalRequirements = criteria.length + requiredEvidence.length;
    const completedItems = completedRequirements.length + presentEvidence.length;
    const completionPercentage = totalRequirements > 0 ? 
      (completedItems / totalRequirements) * 100 : 0;
    
    const isComplete = this.checkCompletion(context);
    
    return {
      isComplete,
      completionPercentage,
      missingRequirements,
      completedRequirements,
      evidence: context.evidence,
      recommendations
    };
  }

  private checkCriterion(context: RichTaskContext, criterion: string): boolean {
    // Check specific criteria based on task type
    switch (context.taskType) {
      case 'simple_question':
        return this.checkSimpleQuestionCriterion(context, criterion);
      case 'coding_task':
        return this.checkCodingTaskCriterion(context, criterion);
      case 'research_task':
        return this.checkResearchTaskCriterion(context, criterion);
      case 'general_task':
        return this.checkGeneralTaskCriterion(context, criterion);
      default:
        return false;
    }
  }

  private checkSimpleQuestionCriterion(context: RichTaskContext, criterion: string): boolean {
    switch (criterion) {
      case 'Answer file created with correct content':
        return this.hasEvidenceType(context, 'file_creation') && 
               context.files.some(f => f.fileType === 'documentation');
      case 'Answer is directly provided to the question':
        return this.hasDirectAnswer(context);
      case 'Evidence of synthesis or direct response':
        return this.hasEvidenceType(context, 'synthesis') || this.hasDirectAnswer(context);
      default:
        return false;
    }
  }

  private checkCodingTaskCriterion(context: RichTaskContext, criterion: string): boolean {
    switch (criterion) {
      case 'Code file created with working implementation':
        return this.hasEvidenceType(context, 'file_creation') && 
               context.files.some(f => f.fileType === 'code' && this.hasWorkingCode(f));
      case 'Code contains actual functions/classes (not just comments)':
        return context.files.some(f => f.fileType === 'code' && this.hasWorkingCode(f));
      case 'Code is properly documented or has inline documentation':
        return this.hasProperCodeDocumentation(context);
      case 'Code file has sufficient complexity to solve the problem':
        return this.hasSufficientCodeComplexity(context);
      default:
        return false;
    }
  }

  private checkResearchTaskCriterion(context: RichTaskContext, criterion: string): boolean {
    switch (criterion) {
      case 'Summary or research document created':
        return this.hasEvidenceType(context, 'file_creation') && 
               context.files.some(f => f.fileType === 'documentation');
      case 'Document contains synthesized findings':
        return this.hasEvidenceType(context, 'synthesis');
      case 'Document has proper structure and organization':
        return context.files.some(f => f.fileType === 'documentation' && this.hasResearchStructure(f));
      case 'Evidence of information gathering and analysis':
        return this.hasInformationGatheringEvidence(context);
      default:
        return false;
    }
  }

  private checkGeneralTaskCriterion(context: RichTaskContext, criterion: string): boolean {
    switch (criterion) {
      case 'Task output file created':
        return this.hasEvidenceType(context, 'file_creation');
      case 'Output contains relevant content':
        return this.hasValidTaskOutput(context);
      case 'Evidence of successful execution':
        return this.hasEvidenceType(context, 'execution');
      default:
        return false;
    }
  }
}
